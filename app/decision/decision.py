"""Decision layer (spec §2.5): assemble the final decision brief from Memory — the
structured recommendation, the three per-axis scores SIDE BY SIDE (never blended), the
mechanically gap-rendered required fields, and the latency strip. No LLM calls: this is a
pure assembly/rendering layer, so it is deterministic and adds zero API cost.
"""
import json

from .. import instrument
from ..memory import ingest
from ..screening import axes as axes_mod

# Required memo fields whose absence must be flagged in the brief's own words, never
# filled with a generated value (P0 guardrail). keyword -> field is a mechanical lookup.
GAP_FIELDS = {
    "Cap table": ["cap table", "ownership", "dilution", "vsop"],
    "Churn": ["churn"],
    "CAC": ["cac", "customer acquisition cost"],
    "Sales cycle": ["sales cycle"],
    "Usage metrics": ["dau", "active users", "usage metric", "usage metrics"],
}
GAP_PHRASE = "not disclosed"
# A claim that itself SAYS the field is missing must not count as disclosure.
_GAPPY = ("not disclosed", "not applicable", "unavailable", "not derivable",
          "not included", "no external corroboration", "not provided", "missing")


def gap_report(claims) -> list[dict]:
    """For each required field: present (cite claim ids) or a gap rendered as the brief's
    phrase. The gap branch NEVER emits a value — only the fixed phrase."""
    texts = [(c.id, c.text.lower()) for c in claims
             if not any(g in c.text.lower() for g in _GAPPY)]
    report = []
    for field, kws in GAP_FIELDS.items():
        hits = [cid for cid, t in texts if any(k in t for k in kws)]
        if hits:
            report.append({"field": field, "status": "present", "claim_ids": hits})
        else:
            report.append({"field": field, "status": "gap",
                           "rendered": f"{field}: {GAP_PHRASE}"})
    return report


def per_axis(conn, founder_id: str, thesis_name: str | None = None) -> list[dict]:
    """Latest score per screening axis, side by side with a trend. Never averaged.
    With thesis_name, only scores produced under that thesis lens count."""
    out = []
    for axis in axes_mod.AXES:
        if thesis_name:
            row = conn.execute(
                "SELECT score, stance, coverage FROM axis_scores WHERE founder_id=? "
                "AND axis=? AND thesis=? ORDER BY scored_at DESC LIMIT 1",
                (founder_id, axis, thesis_name)).fetchone()
        else:
            row = conn.execute(
                "SELECT score, stance, coverage FROM axis_scores WHERE founder_id=? "
                "AND axis=? ORDER BY scored_at DESC LIMIT 1",
                (founder_id, axis)).fetchone()
        if row:
            out.append({"axis": axis, "score": row["score"], "stance": row["stance"],
                        "coverage": row["coverage"],
                        "trend": axes_mod.trend(conn, founder_id, axis)})
        else:
            out.append({"axis": axis, "status": "not yet screened"})
    return out


def build(conn, founder_id: str, thesis) -> dict:
    memo = conn.execute("SELECT decision, recommendation, memo_md FROM memos WHERE "
                        "founder_id=? AND thesis=?", (founder_id, thesis.name)).fetchone()
    claims = ingest.get_claims(conn, founder_id)
    return {
        "founder_id": founder_id,
        "thesis": thesis.name,
        "decision": memo["decision"] if memo else None,
        "recommendation": json.loads(memo["recommendation"]) if memo else None,
        "axes": per_axis(conn, founder_id),          # side by side, unblended
        "gaps": gap_report(claims),
        "latency": instrument.latency_strip(conn, founder_id),
        "memo_md": memo["memo_md"] if memo else None,
    }


def render(brief: dict) -> str:
    """Render the decision brief as markdown (the recommendation + per-axis + gaps +
    latency header, then the memo)."""
    rec = brief["recommendation"] or {}
    lines = [f"# Decision brief — {brief['founder_id']} · thesis: {brief['thesis']}", ""]
    lines.append(f"**Decision:** {brief['decision']}  ·  "
                 f"**Check:** ${rec.get('amount_usd', 0):,}")
    if rec.get("claims_it_turns_on"):
        lines.append(f"**Turns on:** {', '.join(rec['claims_it_turns_on'])}")
    if rec.get("what_would_change_our_mind"):
        lines.append(f"**What would change our mind:** {rec['what_would_change_our_mind']}")

    lines += ["", "## Axes (independent — not averaged)"]
    for a in brief["axes"]:
        if a.get("status"):
            lines.append(f"- **{a['axis']}**: {a['status']}")
        else:
            lines.append(f"- **{a['axis']}**: {a['score']}/10 {a['trend']} "
                         f"[{a['stance']}] · coverage {a['coverage']:.0%}")

    lines += ["", "## Required fields (gaps flagged, never fabricated)"]
    for g in brief["gaps"]:
        if g["status"] == "gap":
            lines.append(f"- {g['rendered']}")
        else:
            lines.append(f"- {g['field']}: disclosed {g['claim_ids']}")

    lat = brief["latency"]
    strip = " → ".join(f"{s} {instrument.fmt(sec)}" for s, sec in lat["stages"])
    lines += ["", "## Latency strip",
              f"{strip}  =  **{instrument.fmt(lat['total_seconds'])}** signal→decision", ""]

    if brief["memo_md"]:
        lines += ["---", "", brief["memo_md"]]
    return "\n".join(lines)
