"""Idempotent seed loader: cold start is never empty (deployment requirement).

The snapshot is a plain SQLite file checked into the repo; loading goes through the
db.connect() seam so the same code seeds both backends (local SQLite or DATABASE_URL
Postgres). No-op when founders exist — safe to call on every boot.
"""
import shutil
import sqlite3

from . import config
from .memory import db

SNAPSHOT = config.FIXTURES / "seed_db.sqlite"
# FK-safe insert order.
TABLES = ["founders", "signals", "claims", "resolutions", "droplog", "axis_scores",
          "adjudications", "memos", "latency", "kill_log", "outreach"]
_SMOKE = "founder-smoke"


def snapshot() -> None:
    """Dump the local vc_brain.db to the repo snapshot, minus smoke-test rows."""
    if not config.DB_PATH.exists():
        raise SystemExit("no local vc_brain.db to snapshot")
    SNAPSHOT.parent.mkdir(exist_ok=True)
    shutil.copy(config.DB_PATH, SNAPSHOT)
    conn = sqlite3.connect(SNAPSHOT)
    conn.execute("DROP TRIGGER IF EXISTS signals_no_update")
    conn.execute("DROP TRIGGER IF EXISTS signals_no_delete")
    for t in TABLES:
        col = "id" if t == "founders" else "founder_id"
        try:
            conn.execute(f"DELETE FROM {t} WHERE {col} LIKE '{_SMOKE}%'")
        except sqlite3.OperationalError:
            pass  # tables without that column keep their rows (harmless)
    conn.commit()
    conn.execute("VACUUM")
    n = conn.execute("SELECT COUNT(*) FROM founders").fetchone()[0]
    print(f"snapshot -> {SNAPSHOT} ({n} founders)")


def ensure_seeded() -> bool:
    """Load the snapshot into the active backend if it has no founders yet."""
    if not SNAPSHOT.exists():
        return False
    target = db.connect()
    db.init_db(target)
    if target.execute("SELECT COUNT(*) c FROM founders").fetchone()["c"] > 0:
        return False
    src = sqlite3.connect(SNAPSHOT)
    src.row_factory = sqlite3.Row
    for t in TABLES:
        rows = src.execute(f"SELECT * FROM {t}").fetchall()
        if not rows:
            continue
        cols = rows[0].keys()
        sql = (f"INSERT INTO {t} ({', '.join(cols)}) "
               f"VALUES ({','.join('?' * len(cols))})")
        for r in rows:
            target.execute(sql, tuple(r[c] for c in cols))
        print(f"seeded {t}: {len(rows)} rows")
    target.commit()
    return True
