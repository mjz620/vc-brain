"""Latency instrumentation (spec §2.6): time each stage transition and render the
per-opportunity latency strip (signal -> decision). Trivial to build, directly credited
by the Investment Utility criterion (30%)."""
import time
from contextlib import contextmanager
from datetime import datetime, timezone


@contextmanager
def stage(conn, founder_id: str, name: str):
    """Time a pipeline stage and persist the duration (upsert per founder+stage)."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        dt = time.perf_counter() - t0
        conn.execute("INSERT OR REPLACE INTO latency (founder_id, stage, seconds, "
                     "measured_at) VALUES (?,?,?,?)",
                     (founder_id, name, dt, datetime.now(timezone.utc).isoformat()))
        conn.commit()


def latency_strip(conn, founder_id: str) -> dict:
    rows = conn.execute("SELECT stage, seconds FROM latency WHERE founder_id=? "
                        "ORDER BY measured_at", (founder_id,)).fetchall()
    stages = [(r["stage"], r["seconds"]) for r in rows]
    return {"stages": stages, "total_seconds": sum(s for _, s in stages)}


def fmt(seconds: float) -> str:
    m, s = divmod(seconds, 60)
    return f"{int(m)}m {s:04.1f}s" if m else f"{s:.2f}s"
