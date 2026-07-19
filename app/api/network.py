"""Sourcing knowledge graph (brief Stretch Goal 3: Sourcing & Network Intelligence).

Two layers, joined:
  1. A curated PUBLIC reference of how notable startups became visible (their
     sourcing channel/program) and who backed them early — a map of known
     outcomes, clearly labelled as illustrative reference, never presented as the
     app's own diligence. Loaded from fixtures/sourcing_reference.json (extensible).
  2. The LIVE channel yield from this instance's own Memory (signals -> resolved
     -> founders per source), so "which channels historically produce quality" is
     answered against both history AND what this pipeline is actually doing now.

Emits a force-graph-ready {nodes, links} structure. Node size encodes influence:
funds by how many of these outcomes they backed, channels by how many startups
they sourced, startups by outcome tier — so the biggest nodes are the biggest
players in the sourcing network.
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
    "Research paper (arXiv)": "arxiv",
    "Academic lab spinout": "arxiv",
    "Open-source community (GitHub)": "github",
}

_TIER_WEIGHT = {"decacorn": 4.0, "ipo": 3.0, "unicorn": 2.5, "acquired": 2.0}


def _load_reference() -> dict:
    return json.loads((config.FIXTURES / "sourcing_reference.json").read_text())


def _live_channels(conn) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT s.source, COUNT(DISTINCT s.id) signals, "
        "COUNT(DISTINCT r.signal_id) resolved, COUNT(DISTINCT r.founder_id) founders "
        "FROM signals s LEFT JOIN resolutions r ON r.signal_id = s.id "
        "GROUP BY s.source").fetchall()
    return {r["source"]: {
        "signals": r["signals"], "resolved": r["resolved"], "founders": r["founders"],
        "resolve_rate": round(r["resolved"] / r["signals"], 2) if r["signals"] else 0,
    } for r in rows}


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

    # --- force-graph nodes + links ---
    nodes = []
    for ch in ref["channels"]:
        nodes.append({"id": f"ch:{ch}", "type": "channel", "label": ch,
                      "size": by_channel.get(ch, 0),
                      "cluster": ch, "covered_live": ch in _CHANNEL_TO_LIVE})
    for s in startups:
        nodes.append({"id": f"st:{s['name']}", "type": "startup", "label": s["name"],
                      "size": _TIER_WEIGHT.get(s["tier"], 1.5), "cluster": s["channel"],
                      "sector": s["sector"], "outcome": s["outcome"], "tier": s["tier"]})
    for inv, c in investor_counts.items():
        nodes.append({"id": f"inv:{inv}", "type": "investor", "label": inv,
                      "size": float(c), "cluster": "investor",
                      "backed": investor_startups[inv]})

    links = []
    for s in startups:
        links.append({"source": f"ch:{s['channel']}", "target": f"st:{s['name']}",
                      "kind": "sourced"})
        for inv in s["investors"]:
            links.append({"source": f"st:{s['name']}", "target": f"inv:{inv}",
                          "kind": "seed"})

    # --- channel intelligence: history + this instance's live yield ---
    channel_intel = []
    for ch, desc in ref["channels"].items():
        live_src = _CHANNEL_TO_LIVE.get(ch)
        channel_intel.append({
            "channel": ch, "description": desc,
            "historical_successes": by_channel.get(ch, 0),
            "notable": [s["name"] for s in startups if s["channel"] == ch][:4],
            "live_source": live_src, "live": live.get(live_src) if live_src else None,
            "covered_live": bool(live_src and live_src in live),
        })
    channel_intel.sort(key=lambda c: c["historical_successes"], reverse=True)

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
        "nodes": nodes,
        "links": links,
        "channel_intelligence": channel_intel,
        "top_investors": top_investors,
        "underexplored_channels": underexplored,
        "live_channels": live,
        "counts": {"startups": len(startups), "channels": len(ref["channels"]),
                   "investors": len(investor_counts), "edges": len(links)},
    }
