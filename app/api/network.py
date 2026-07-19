"""Sourcing knowledge graph (brief Stretch Goal 3: Sourcing & Network Intelligence).

Two layers, joined:
  1. A curated PUBLIC reference of how notable startups became visible (their
     sourcing channel/program) and who backed them early — a map of known
     outcomes, clearly labelled as illustrative reference, never presented as the
     app's own diligence. Loaded from fixtures/sourcing_reference.json.
  2. The LIVE channel yield from this instance's own Memory (signals -> resolved
     -> founders per source), so "which channels historically produce quality" is
     answered against both history AND what this pipeline is actually doing now.

The join surfaces the real insight: channels that produced historical successes
but that this scanner doesn't cover yet (Thiel Fellowship, lab spinouts) are the
underexplored sourcing edges worth adding.
"""
import json
from collections import Counter

from fastapi import APIRouter

from .. import config
from ..memory import db

router = APIRouter(prefix="/api")

# Reference sourcing channel -> the live scan source that covers it (if any).
_CHANNEL_TO_LIVE = {
    "Y Combinator": "yc",
    "Academic lab spinout": "arxiv",
    "Research lab spinout": "arxiv",
}


def _load_reference() -> dict:
    path = config.FIXTURES / "sourcing_reference.json"
    return json.loads(path.read_text())


def _live_channels(conn) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT s.source, COUNT(DISTINCT s.id) signals, "
        "COUNT(DISTINCT r.signal_id) resolved, COUNT(DISTINCT r.founder_id) founders "
        "FROM signals s LEFT JOIN resolutions r ON r.signal_id = s.id "
        "GROUP BY s.source").fetchall()
    out = {}
    for r in rows:
        out[r["source"]] = {
            "signals": r["signals"], "resolved": r["resolved"],
            "founders": r["founders"],
            "resolve_rate": round(r["resolved"] / r["signals"], 2) if r["signals"] else 0,
        }
    return out


@router.get("/network")
def network():
    ref = _load_reference()
    conn = db.connect()
    live = _live_channels(conn)

    startups = ref["startups"]
    by_channel = Counter(s["channel"] for s in startups)
    investor_counts = Counter()
    investor_startups: dict[str, list] = {}
    for s in startups:
        for inv in s["investors"]:
            investor_counts[inv] += 1
            investor_startups.setdefault(inv, []).append(s["name"])

    # Channel intelligence: historical success count + this instance's live yield.
    channel_intel = []
    for ch, desc in ref["channels"].items():
        n = by_channel.get(ch, 0)
        live_src = _CHANNEL_TO_LIVE.get(ch)
        channel_intel.append({
            "channel": ch,
            "description": desc,
            "historical_successes": n,
            "notable": [s["name"] for s in startups if s["channel"] == ch][:4],
            "live_source": live_src,
            "live": live.get(live_src) if live_src else None,
            "covered_live": bool(live_src and live_src in live),
        })
    channel_intel.sort(key=lambda c: c["historical_successes"], reverse=True)

    # Investors backing >1 of these outcomes — the network hubs.
    top_investors = [
        {"name": inv, "count": c, "startups": investor_startups[inv]}
        for inv, c in investor_counts.most_common() if c >= 2
    ]

    underexplored = [c["channel"] for c in channel_intel
                     if c["historical_successes"] >= 1 and not c["covered_live"]]

    return {
        "note": ref["_provenance"],
        "channels": ref["channels"],
        "startups": startups,
        "channel_intelligence": channel_intel,
        "top_investors": top_investors,
        "underexplored_channels": underexplored,
        "live_channels": live,
    }
