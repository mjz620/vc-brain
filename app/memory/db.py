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
