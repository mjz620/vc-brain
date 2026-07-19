"""Memory layer: connection + schema (founders, signals, claims).

Two backends behind one seam:
- SQLite (default): stdlib sqlite3, zero ops — local dev, tests (`:memory:`), replay.
- Postgres (Supabase): set DATABASE_URL and `connect()` returns a pooled psycopg
  connection wrapped in a proxy that translates the app's SQLite dialect (`?`
  placeholders, INSERT OR REPLACE, GROUP_CONCAT) so the 80+ call sites stay
  untouched. Judge-submitted founders persist across host restarts.

The signals table is enforced append-only by triggers on BOTH engines — "nothing
discarded" is a brief requirement and the append-only table *is* the compliance
story (spec §2.1).
"""
import os
import re
import sqlite3
import threading
import weakref

from .. import config

# Engine-neutral DDL (valid on SQLite and Postgres).
_COMMON = """
CREATE TABLE IF NOT EXISTS founders (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    aliases       TEXT NOT NULL DEFAULT '[]',   -- JSON
    entity_keys   TEXT NOT NULL DEFAULT '{}',   -- JSON
    founder_score TEXT,                          -- JSON (dimensions + coverage + history)
    first_seen    TEXT,
    last_updated  TEXT
);

CREATE TABLE IF NOT EXISTS signals (
    id          TEXT PRIMARY KEY,               -- "sig-" + dedup_hash[:12] (content-stable)
    founder_id  TEXT REFERENCES founders(id),   -- nullable until resolved
    source      TEXT NOT NULL,
    source_url  TEXT NOT NULL,
    content     TEXT NOT NULL,
    observed_at TEXT,
    ingested_at TEXT NOT NULL,
    dedup_hash  TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_signals_founder ON signals(founder_id);

-- Every claim must trace to resolvable evidence: evidence_url is non-empty by
-- CHECK constraint. Negative results carry the search URL that returned nothing.
CREATE TABLE IF NOT EXISTS claims (
    claim_id      TEXT NOT NULL,                -- e.g. "team-03"
    founder_id    TEXT NOT NULL REFERENCES founders(id),
    axis          TEXT NOT NULL,
    text          TEXT NOT NULL,
    stance        TEXT NOT NULL,
    evidence      TEXT NOT NULL,
    evidence_url  TEXT NOT NULL CHECK (evidence_url <> ''),
    evidence_title   TEXT,                      -- human-readable source title
    evidence_excerpt TEXT,                      -- verbatim snippet backing the claim
    retrieved_at  TEXT,                         -- when the evidence was fetched
    source_type   TEXT NOT NULL,
    corroboration TEXT NOT NULL,
    trust         REAL NOT NULL,
    observed_at   TEXT,
    signal_ids    TEXT NOT NULL DEFAULT '[]',   -- JSON: >=1 signal per claim
    PRIMARY KEY (founder_id, claim_id)
);

-- Entity resolution: a signal links to a founder only on >=2 co-occurring entity
-- keys. Resolution is its own ledger so raw signals stay immutable.
CREATE TABLE IF NOT EXISTS resolutions (
    signal_id   TEXT PRIMARY KEY REFERENCES signals(id),
    founder_id  TEXT NOT NULL REFERENCES founders(id),
    method      TEXT NOT NULL,
    resolved_at TEXT NOT NULL
);

-- Drop-log: signals that failed entity resolution are logged, not discarded
-- (spec §2.1 "nothing discarded"; the drop-log is the compliance story).
CREATE TABLE IF NOT EXISTS droplog (
    signal_id   TEXT NOT NULL,
    reason      TEXT NOT NULL,
    entity_keys TEXT NOT NULL DEFAULT '{}',
    logged_at   TEXT NOT NULL
);

-- Per-opportunity axis scores (spec §2.3). Three independent axes, NEVER averaged.
-- Append-only, so the trend over time falls out by comparing successive scores.
CREATE TABLE IF NOT EXISTS axis_scores (
    founder_id TEXT NOT NULL REFERENCES founders(id),
    axis       TEXT NOT NULL,           -- founder | market | idea
    score      REAL NOT NULL,           -- 0–10
    stance     TEXT NOT NULL,
    rationale  TEXT NOT NULL,
    coverage   REAL NOT NULL,           -- 0–1
    thesis     TEXT NOT NULL,
    scored_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_axis_founder ON axis_scores(founder_id, axis);

-- Adjudication verdicts (fact-layer debate): the Judge's tier/trust decision on a
-- contested claim, with the prosecution/defense it turned on. Append-only audit trail.
CREATE TABLE IF NOT EXISTS adjudications (
    founder_id  TEXT NOT NULL REFERENCES founders(id),
    claim_id    TEXT NOT NULL,
    prosecution TEXT NOT NULL,
    defense     TEXT NOT NULL,
    corroboration TEXT NOT NULL,   -- Judge-set tier
    trust       REAL NOT NULL,     -- Judge-set trust
    rationale   TEXT NOT NULL,
    decided_at  TEXT NOT NULL
);

-- Final memo + recommendation from the diligence pipeline (decision-layer debate).
CREATE TABLE IF NOT EXISTS memos (
    founder_id     TEXT NOT NULL REFERENCES founders(id),
    thesis         TEXT NOT NULL,
    decision       TEXT NOT NULL,          -- invest | pass | conditional
    recommendation TEXT NOT NULL,          -- JSON (structured recommendation)
    memo_md        TEXT NOT NULL,          -- the memo (markdown, cites claim ids)
    bull           TEXT NOT NULL,
    bear           TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    PRIMARY KEY (founder_id, thesis)
);

-- Latency instrumentation (spec §2.6): per-stage wall-clock, signal -> decision.
-- Directly credited by the Investment Utility criterion (30%).
CREATE TABLE IF NOT EXISTS latency (
    founder_id  TEXT NOT NULL,
    stage       TEXT NOT NULL,
    seconds     REAL NOT NULL,
    measured_at TEXT NOT NULL,
    PRIMARY KEY (founder_id, stage)
);

-- First-pass kill screen (spec §2.3): log why a non-viable opportunity was killed.
CREATE TABLE IF NOT EXISTS kill_log (
    founder_id TEXT NOT NULL,
    reason     TEXT NOT NULL,
    thesis     TEXT NOT NULL,
    logged_at  TEXT NOT NULL
);

-- Live run progress (apply -> memo): one row per (founder, stage), rewritten as the
-- pipeline advances so the UI can render a watchable run. Errors land in detail.
CREATE TABLE IF NOT EXISTS run_status (
    founder_id TEXT NOT NULL,
    stage      TEXT NOT NULL,           -- ingest|screen|extract|adjudicate|debate|synthesize|done
    status     TEXT NOT NULL,           -- queued | running | ok | error
    detail     TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (founder_id, stage)
);

-- Activate (brief MVP 5): outreach drafts, each tied to the signal that triggered it.
CREATE TABLE IF NOT EXISTS outreach (
    founder_id TEXT NOT NULL REFERENCES founders(id),
    signal_id  TEXT NOT NULL REFERENCES signals(id),
    subject    TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (founder_id, signal_id)
);
"""

# Append-only guard: the signals table cannot be updated or deleted from.
_SQLITE_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS signals_no_update BEFORE UPDATE ON signals
BEGIN SELECT RAISE(ABORT, 'signals table is append-only'); END;
CREATE TRIGGER IF NOT EXISTS signals_no_delete BEFORE DELETE ON signals
BEGIN SELECT RAISE(ABORT, 'signals table is append-only'); END;
"""

_PG_TRIGGERS = """
CREATE OR REPLACE FUNCTION signals_append_only() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'signals table is append-only'; END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS signals_no_update ON signals;
CREATE TRIGGER signals_no_update BEFORE UPDATE ON signals
FOR EACH ROW EXECUTE FUNCTION signals_append_only();
DROP TRIGGER IF EXISTS signals_no_delete ON signals;
CREATE TRIGGER signals_no_delete BEFORE DELETE ON signals
FOR EACH ROW EXECUTE FUNCTION signals_append_only();
"""

SCHEMA = _COMMON + _SQLITE_TRIGGERS
PG_SCHEMA = _COMMON + _PG_TRIGGERS


# ---------------------------------------------------------------------------
# Postgres proxy: translate the app's SQLite dialect at the connection seam.
# ---------------------------------------------------------------------------

# Conflict targets for INSERT OR REPLACE rewrites (every such table has a PK).
_PG_PK = {
    "founders": ("id",),
    "signals": ("id",),
    "claims": ("founder_id", "claim_id"),
    "resolutions": ("signal_id",),
    "memos": ("founder_id", "thesis"),
    "latency": ("founder_id", "stage"),
    "outreach": ("founder_id", "signal_id"),
}

_RE_IOR = re.compile(r"^\s*INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\(([^)]+)\)", re.I)
_RE_GC_DISTINCT = re.compile(r"GROUP_CONCAT\(\s*DISTINCT\s+([^)]+?)\s*\)", re.I)
_RE_GC_SEP = re.compile(r"GROUP_CONCAT\(\s*([^,()]+?)\s*,\s*'([^']*)'\s*\)", re.I | re.S)


def _to_pg(sql: str) -> str:
    m = _RE_IOR.match(sql)
    if m:
        table = m.group(1)
        cols = [c.strip() for c in m.group(2).split(",")]
        pk = _PG_PK[table]
        updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c not in pk)
        sql = _RE_IOR.sub(f"INSERT INTO {table} ({', '.join(cols)})", sql, count=1)
        sql = f"{sql} ON CONFLICT ({', '.join(pk)}) DO UPDATE SET {updates}"
    sql = _RE_GC_DISTINCT.sub(lambda g: f"STRING_AGG(DISTINCT {g.group(1)}, ',')", sql)
    sql = _RE_GC_SEP.sub(lambda g: f"STRING_AGG({g.group(1)}, '{g.group(2)}')", sql)
    return sql.replace("?", "%s")


class _EmptyResult:
    def fetchone(self):
        return None

    def fetchall(self):
        return []


def _putback(pool, raw):
    try:
        pool.putconn(raw)  # putconn rolls back any open transaction
    except Exception:
        try:
            raw.close()
        except Exception:
            pass


class PgConnection:
    """Duck-types the sqlite3.Connection surface the app uses:
    execute()/commit()/close(), with cursor.fetchone()/fetchall() dict rows.
    Returned to the pool when garbage-collected (CPython refcounting makes this
    prompt at request end) or on explicit close()."""

    def __init__(self, raw, pool):
        self._raw = raw
        self._finalizer = weakref.finalize(self, _putback, pool, raw)

    def execute(self, sql: str, params=()):
        if sql.lstrip().upper().startswith("PRAGMA"):
            return _EmptyResult()
        return self._raw.execute(_to_pg(sql), params)

    def executescript(self, script: str):
        self._raw.execute(script)

    def commit(self):
        self._raw.commit()

    def close(self):
        self._finalizer()


_pool = None
_pool_lock = threading.Lock()
_pg_initialized = False


def _get_pool():
    global _pool
    with _pool_lock:
        if _pool is None:
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool

            def _configure(c):
                c.row_factory = dict_row
                # Supabase pooler (transaction mode) breaks server-side prepares.
                c.prepare_threshold = None

            _pool = ConnectionPool(
                os.environ["DATABASE_URL"], min_size=0, max_size=5,
                configure=_configure, open=True)
        return _pool


# ---------------------------------------------------------------------------
# Public seam — unchanged signatures.
# ---------------------------------------------------------------------------

def connect(path=None):
    url = os.environ.get("DATABASE_URL")
    if url and path is None:
        pool = _get_pool()
        return PgConnection(pool.getconn(), pool)
    conn = sqlite3.connect(path or config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn) -> None:
    global _pg_initialized
    if isinstance(conn, PgConnection):
        if _pg_initialized:
            return
        conn.executescript(PG_SCHEMA)
        conn.commit()
        _pg_initialized = True
        return
    conn.executescript(SCHEMA)
    conn.commit()
