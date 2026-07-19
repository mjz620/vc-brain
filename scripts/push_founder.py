"""Copy ONE founder's rows from the local SQLite DB into the active backend
(DATABASE_URL Postgres if set, else local). Idempotent: skips rows already present.
Used to add the real-company showcase to the deployed Supabase without a full reseed.

Usage: .venv/bin/python scripts/push_founder.py founder-langfuse
"""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import config  # noqa: E402
from app.memory import db  # noqa: E402

# founder-keyed tables to copy (signals first is fine; FKs are permissive).
BY_FOUNDER = ["founders", "signals", "claims", "axis_scores", "adjudications",
              "memos", "latency", "kill_log", "outreach", "resolutions", "run_status"]
# Tables with no primary key are append-only style: plain INSERT (INSERT OR REPLACE
# has no conflict target and the Postgres proxy can't rewrite it).
_NO_PK = {"axis_scores", "adjudications", "kill_log", "run_status", "droplog"}


def main(fid: str):
    src = sqlite3.connect(ROOT / "vc_brain.db")
    src.row_factory = sqlite3.Row
    dst = db.connect()
    db.init_db(dst)
    for t in BY_FOUNDER:
        key = "id" if t == "founders" else "founder_id"
        try:
            rows = src.execute(f"SELECT * FROM {t} WHERE {key} = ?", (fid,)).fetchall()
        except sqlite3.OperationalError:
            continue
        if not rows:
            continue
        cols = rows[0].keys()
        placeholders = ",".join("?" * len(cols))
        verb = "INSERT" if t in _NO_PK else "INSERT OR REPLACE"
        n = 0
        for r in rows:
            try:
                dst.execute(
                    f"{verb} INTO {t} ({', '.join(cols)}) "
                    f"VALUES ({placeholders})", tuple(r[c] for c in cols))
                n += 1
            except Exception as e:  # already present / append-only signal: skip
                print(f"  {t}: skipped a row ({type(e).__name__})")
        dst.commit()
        print(f"{t}: pushed {n}/{len(rows)}")
    print(f"done -> {'Postgres' if config.__dict__.get('_') is None and __import__('os').environ.get('DATABASE_URL') else 'SQLite'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "founder-langfuse")
