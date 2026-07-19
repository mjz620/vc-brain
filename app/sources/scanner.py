"""Outbound scan orchestrator: thesis topics -> all source adapters -> Memory -> resolve.

The thesis drives the queries (spec §2.5: the thesis is "applied twice: as a filter on
the sourcing scanner and as a scoring lens in screening"). A source failing must never
sink the scan; its error is reported in the per-source counts instead.
"""
from ..memory import resolve
from ..screening import thesis as thesis_mod
from . import arxiv, github, hn, launchtracker, producthunt, websearch, yc

ADAPTERS = [("github", github.scan), ("hn", hn.scan), ("arxiv", arxiv.scan),
            ("producthunt", producthunt.scan), ("yc", yc.scan),
            ("launchtracker", launchtracker.scan),
            ("websearch", websearch.scan)]


def run_scan(conn, topics: list[str], *, replay: bool, limit_per: int = 8,
             sources: list[str] | None = None) -> dict:
    """Scan every topic across every adapter, ingest, then entity-resolve the batch.

    Returns {"items", "counts": {source: n|"error: .."}, "resolved", "dropped",
    "founders", "new_signal_ids"}.
    """
    items: list[dict] = []
    counts: dict[str, object] = {}
    for name, fn in ADAPTERS:
        if sources and name not in sources:
            continue
        n = 0
        for topic in topics:
            try:
                found = fn(conn, topic, replay=replay, limit=limit_per)
                items += found
                n += len(found)
            except Exception as e:  # noqa: BLE001 — a source failing must not sink the scan
                counts[name] = f"error: {type(e).__name__}: {e}"
                break
        else:
            counts[name] = n

    summary = resolve.resolve(conn, items)
    return {
        "items": items,
        "counts": counts,
        "resolved": summary["resolved"],
        "dropped": summary["dropped"],
        "founders": summary["founders"],
        "new_signal_ids": [it["signal_id"] for it in items if it.get("inserted")],
    }


def topics_for(thesis: thesis_mod.Thesis, override: str | None = None) -> list[str]:
    """Scan queries: an explicit --topic override wins, else the thesis drives them."""
    return [override] if override else thesis_mod.sourcing_topics(thesis)


def newly_resolved_founders(conn, new_signal_ids: list[str]) -> list[tuple[str, int]]:
    """Founders that gained resolved signals in this batch, most-new first."""
    if not new_signal_ids:
        return []
    marks = ",".join("?" * len(new_signal_ids))
    rows = conn.execute(
        f"SELECT founder_id, COUNT(*) n FROM resolutions WHERE signal_id IN ({marks}) "
        "GROUP BY founder_id ORDER BY n DESC", new_signal_ids).fetchall()
    return [(r["founder_id"], r["n"]) for r in rows]
