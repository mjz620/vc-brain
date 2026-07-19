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
from ..memory import db, founder_score

router = APIRouter(prefix="/api")

# Reference sourcing channel -> the live scan source that covers it (if any).
_CHANNEL_TO_LIVE = {
    "Y Combinator": "yc",
    "Research paper (arXiv)": "arxiv",
    "Academic lab spinout": "arxiv",
    "Open-source community (GitHub)": "github",
}

# Live scan source -> the reference channel node its founders attach to. Sources
# with no historical reference (hn, producthunt) get their own live-only hub below.
_LIVE_TO_CHANNEL = {
    "yc": "Y Combinator",
    "arxiv": "Research paper (arXiv)",
    "github": "Open-source community (GitHub)",
}
_LIVE_ONLY_HUBS = {"hn": "Hacker News", "producthunt": "Product Hunt"}

_TIER_WEIGHT = {"decacorn": 4.0, "ipo": 3.0, "unicorn": 2.5, "acquired": 2.0}


def _live_founders(conn) -> list[dict]:
    """This pipeline's own sourced founders + the channel each came in through.

    A founder's channel is their most-frequent signal source. Node size comes from
    the canonical Signal score (founder_score.compute_batch) — the same metric shown
    everywhere else — so a founder we scored high shows up bigger. This is the LIVE
    layer overlaid on the historical reference: who WE are sourcing, right now."""
    rows = conn.execute(
        "SELECT f.id id, f.name name, s.source source, COUNT(*) c "
        "FROM founders f JOIN resolutions r ON r.founder_id = f.id "
        "JOIN signals s ON s.id = r.signal_id "
        "GROUP BY f.id, s.source").fetchall()
    top: dict[str, tuple[str, str, int]] = {}
    for r in rows:
        cur = top.get(r["id"])
        if cur is None or r["c"] > cur[2]:
            top[r["id"]] = (r["name"], r["source"], r["c"])
    if not top:
        return []
    scores = founder_score.compute_batch(conn, list(top))
    out = []
    for fid, (name, source, _) in top.items():
        out.append({"id": fid, "name": name, "source": source,
                    "score": (scores.get(fid) or {}).get("score")})
    return out


def _load_reference() -> dict:
    return json.loads((config.FIXTURES / "sourcing_reference.json").read_text())


def _channel_outcomes(conn, live_founders: list[dict]) -> dict[str, dict]:
    """Close the loop: join this fund's OWN realized decisions back to the channel
    that sourced each founder.

    Two distinct quantities, kept separate on purpose because they are not equally
    populated and conflating them would overstate what the graph knows:

    `quality`  — median Signal score of the founders a channel produced. Populated
                 today across every channel, so it is what node glow encodes.
    `outcomes` — screened / killed / invested / passed counts from kill_log and
                 memos. This is genuine outcome data, but it is thin early on, so
                 `decided` is reported honestly and `decision_yield` stays None until
                 a channel actually has decisions. An unlit channel means "no
                 decisions yet", never "performed badly".
    """
    by_source: dict[str, list[float]] = {}
    fids_by_source: dict[str, list[str]] = {}
    for f in live_founders:
        fids_by_source.setdefault(f["source"], []).append(f["id"])
        if f["score"] is not None:
            by_source.setdefault(f["source"], []).append(f["score"])

    killed = {r["founder_id"] for r in
              conn.execute("SELECT DISTINCT founder_id FROM kill_log").fetchall()}
    decisions = {r["founder_id"]: r["decision"] for r in
                 conn.execute("SELECT founder_id, decision FROM memos").fetchall()}

    out: dict[str, dict] = {}
    for source, fids in fids_by_source.items():
        scores = sorted(by_source.get(source, []))
        median = scores[len(scores) // 2] if scores else None
        decided = [decisions[f] for f in fids if f in decisions]
        positive = sum(1 for d in decided if d in ("invest", "conditional"))
        out[source] = {
            "founders": len(fids),
            "median_signal": median,
            # Glow: median Signal normalised to 0-1. Real, populated, and labelled
            # for what it is — NOT a claim about realised founder success.
            "glow": round(median / 10.0, 3) if median is not None else None,
            "screen_killed": sum(1 for f in fids if f in killed),
            "decided": len(decided),
            "invested": sum(1 for d in decided if d == "invest"),
            "passed": sum(1 for d in decided if d == "pass"),
            "conditional": sum(1 for d in decided if d == "conditional"),
            "decision_yield": round(positive / len(decided), 2) if decided else None,
        }
    return out


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

    # --- LIVE overlay: this pipeline's own founders, wired to their channel ---
    live_founders = _live_founders(conn)
    outcomes = _channel_outcomes(conn, live_founders)
    # Channel nodes glow by the median Signal of the founders they produced. A channel
    # this instance has never sourced from has no glow at all, rather than a dim one.
    for n in nodes:
        if n["type"] == "channel":
            src = _CHANNEL_TO_LIVE.get(n["label"])
            n["glow"] = (outcomes.get(src) or {}).get("glow") if src else None
    ref_channel_ids = {f"ch:{ch}" for ch in ref["channels"]}
    live_hub_counts = Counter(f["source"] for f in live_founders
                              if f["source"] in _LIVE_ONLY_HUBS)
    for src, label in _LIVE_ONLY_HUBS.items():
        if live_hub_counts.get(src):
            nodes.append({"id": f"ch:{label}", "type": "channel", "label": label,
                          "size": live_hub_counts[src], "cluster": label,
                          "covered_live": True, "live_only": True,
                          "glow": (outcomes.get(src) or {}).get("glow")})
    for f in live_founders:
        ch = _LIVE_TO_CHANNEL.get(f["source"]) or _LIVE_ONLY_HUBS.get(f["source"])
        target = f"ch:{ch}" if ch else None
        if not target or (target not in ref_channel_ids and f["source"] not in _LIVE_ONLY_HUBS):
            continue  # source with no channel to attach to — skip rather than orphan
        nodes.append({"id": f"fr:{f['id']}", "type": "founder", "label": f["name"],
                      "size": f["score"] if f["score"] is not None else 0.0,
                      "cluster": ch, "signal": f["score"], "source": f["source"],
                      "glow": round(f["score"] / 10.0, 3) if f["score"] is not None
                              else None})
        links.append({"source": f"fr:{f['id']}", "target": target, "kind": "live"})
    live_founder_n = sum(1 for n in nodes if n["type"] == "founder")

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
            "outcomes": outcomes.get(live_src) if live_src else None,
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
        "channel_outcomes": outcomes,
        "glow_encodes": ("median Signal score of the founders each channel produced "
                         "(0-1). Realised decision yield is reported separately in "
                         "channel_outcomes.decision_yield and is null until a channel "
                         "has decisions — unlit means no data, not poor performance."),
        "counts": {"startups": len(startups), "channels": len(ref["channels"]),
                   "investors": len(investor_counts), "edges": len(links),
                   "live_founders": live_founder_n},
    }
