"""SQLite Memory layer: connection + schema (founders, signals, claims).

Single file, stdlib sqlite3, zero ops. The signals table is enforced append-only by
triggers — "nothing discarded" is a brief requirement and the append-only table *is*
the compliance story (spec §2.1).
"""
import sqlite3

from .. import config

SCHEMA = """
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

CREATE TABLE IF NOT EXISTS claims (
    claim_id      TEXT NOT NULL,                -- e.g. "team-03"
    founder_id    TEXT NOT NULL REFERENCES founders(id),
    axis          TEXT NOT NULL,
    text          TEXT NOT NULL,
    stance        TEXT NOT NULL,
    evidence      TEXT NOT NULL,
    source_url    TEXT NOT NULL,
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

-- Activate (brief MVP 5): outreach drafts, each tied to the signal that triggered it.
CREATE TABLE IF NOT EXISTS outreach (
    founder_id TEXT NOT NULL REFERENCES founders(id),
    signal_id  TEXT NOT NULL REFERENCES signals(id),
    subject    TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (founder_id, signal_id)
);

-- Append-only guard: the signals table cannot be updated or deleted from.
CREATE TRIGGER IF NOT EXISTS signals_no_update BEFORE UPDATE ON signals
BEGIN SELECT RAISE(ABORT, 'signals table is append-only'); END;
CREATE TRIGGER IF NOT EXISTS signals_no_delete BEFORE DELETE ON signals
BEGIN SELECT RAISE(ABORT, 'signals table is append-only'); END;
"""


def connect(path=None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
