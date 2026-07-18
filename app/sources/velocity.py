"""Execution-velocity fetch: the cold-start instrument (spec §3 — "velocity over
volume": commit cadence over the trailing 6 weeks, not accumulated pedigree).

One GitHub commits call per founder repo (keyless, cached). The window start is fixed
relative to DEMO_TODAY so the cache key — and therefore replay — stays deterministic.
The result is ingested as a first-class signal, so it feeds screening summaries and
the Founder Score the same way any other evidence does.
"""
import re

from ..memory import ingest
from ..memory.models import Signal
from .http import get_json

_REPO = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)")
SINCE = "2026-06-06T00:00:00Z"  # DEMO_TODAY minus 6 weeks, fixed for stable cache keys


def repo_of(conn, founder_id: str) -> str | None:
    """The founder's most-starred GitHub repo, from their resolved signals."""
    rows = conn.execute(
        "SELECT s.source_url, s.content FROM signals s "
        "LEFT JOIN resolutions r ON r.signal_id = s.id "
        "WHERE (r.founder_id = ? OR s.founder_id = ?) AND s.source = 'github' "
        "AND s.content NOT LIKE 'velocity:%'", (founder_id, founder_id)).fetchall()
    best, best_stars = None, -1
    for r in rows:
        m = _REPO.match(r["source_url"])
        if not m:
            continue
        stars = re.search(r"stars=(\d+)", r["content"])
        n = int(stars.group(1)) if stars else 0
        if n > best_stars:
            best, best_stars = m.group(1), n
    return best


def fetch(conn, founder_id: str, *, replay: bool) -> dict | None:
    """Fetch trailing-6-week commit cadence for the founder's main repo -> Signal."""
    full = repo_of(conn, founder_id)
    if not full:
        return None
    commits = get_json(f"https://api.github.com/repos/{full}/commits",
                       {"since": SINCE, "per_page": 100}, replay=replay)
    if not isinstance(commits, list):
        return None
    days = {(c.get("commit", {}).get("author", {}) or {}).get("date", "")[:10]
            for c in commits}
    days.discard("")
    content = (f"velocity: commits_6w={len(commits)} active_days={len(days)} "
               f"window_since={SINCE[:10]} repo={full}")
    sig = Signal(source="github", source_url=f"https://github.com/{full}/commits",
                 content=content, founder_id=founder_id)
    ingest.ingest_signal(conn, sig)
    return {"repo": full, "commits_6w": len(commits), "active_days": len(days)}
