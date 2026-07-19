"""One-time migration: claims.source_url -> evidence_url (required, non-empty) +
evidence_title / evidence_excerpt / retrieved_at columns + signal_ids backfill.

Backfill is mechanical only — titles come from the matched signal row, excerpts from
the claim's own stored evidence snippet. No value is generated. Idempotent: skips
databases already on the new schema. SQLite only (Postgres starts on the new schema).
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import config  # noqa: E402


def migrate(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(claims)")}
    if "evidence_url" in cols:
        print(f"{path}: already migrated")
        return
    if "source_url" not in cols:
        print(f"{path}: no claims table yet")
        return
    conn.execute("ALTER TABLE claims RENAME COLUMN source_url TO evidence_url")
    conn.execute("ALTER TABLE claims ADD COLUMN evidence_title TEXT")
    conn.execute("ALTER TABLE claims ADD COLUMN evidence_excerpt TEXT")
    conn.execute("ALTER TABLE claims ADD COLUMN retrieved_at TEXT")

    empty = conn.execute("SELECT COUNT(*) c FROM claims WHERE evidence_url IS NULL "
                         "OR evidence_url = ''").fetchone()["c"]
    if empty:
        raise SystemExit(f"{path}: {empty} claims have no evidence_url — cannot "
                         "migrate; these must be adjudicated by hand, not patched")

    n_linked = 0
    for row in conn.execute("SELECT founder_id, claim_id, evidence_url, evidence, "
                            "signal_ids FROM claims").fetchall():
        sigs = conn.execute("SELECT id, content, ingested_at FROM signals "
                            "WHERE source_url = ?", (row["evidence_url"],)).fetchall()
        sig_ids = json.loads(row["signal_ids"] or "[]") or [s["id"] for s in sigs]
        title = sigs[0]["content"].split("|")[0].strip()[:120] if sigs else None
        retrieved = sigs[0]["ingested_at"] if sigs else None
        conn.execute(
            "UPDATE claims SET signal_ids=?, evidence_title=?, evidence_excerpt=?, "
            "retrieved_at=? WHERE founder_id=? AND claim_id=?",
            (json.dumps(sig_ids), title, row["evidence"], retrieved,
             row["founder_id"], row["claim_id"]))
        n_linked += bool(sig_ids)
    conn.commit()
    total = conn.execute("SELECT COUNT(*) c FROM claims").fetchone()["c"]
    print(f"{path}: migrated {total} claims, {n_linked} with resolved signal links")


if __name__ == "__main__":
    migrate(sys.argv[1] if len(sys.argv) > 1 else config.DB_PATH)
