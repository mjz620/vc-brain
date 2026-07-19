"""Scoring transparency: every formula/weight/rubric served straight from the real
code constants (WEIGHTS, COVERAGE_AREAS, TRUST_RUBRIC) and the actual prompt text
used at scoring time — never a hand-typed paraphrase that could drift from what the
system actually computes. Pass ?founder_id= for that founder's real derivation
(the actual numbers that produced their score), not just the general formula.
"""
from fastapi import APIRouter, HTTPException

from .. import config, llm, promptlib
from ..diligence.ledger import CONTESTED_TIERS, TRUST_RUBRIC
from ..memory import db, founder_score, ingest
from ..screening.axes import _DEFAULTS as AXIS_DEFAULTS
from ..screening.axes import _COMMON as AXIS_COMMON

router = APIRouter(prefix="/api")

_TIER_DEFS = {
    "corroborated": "≥2 independent sources agree — the strongest tier.",
    "single_source": "one external source backs the claim, not yet corroborated.",
    "self_reported": "only the founder's own deck/word — no external backing. Capped low regardless of how impressive the claim.",
    "contradicted": "external evidence conflicts with the claim, or a negative-result search found nothing where something was claimed.",
}

_PROVIDER_MODEL = {
    "screen": lambda p: "claude-haiku-4-5" if p == "anthropic" else config.openai_model("screen"),
    "worker": lambda p: "claude-sonnet-5" if p == "anthropic" else config.openai_model("worker"),
    "synth": lambda p: "claude-opus-4-8" if p == "anthropic" else config.openai_model("synth"),
}


def _axis_methodology() -> dict:
    p = llm.provider() or "anthropic"  # report the tier that WOULD run; replay works with none
    out = {}
    for axis, default in AXIS_DEFAULTS.items():
        rubric_text = promptlib.load_prompt(f"rubric_{axis}", default + AXIS_COMMON)
        out[axis] = {"rubric": rubric_text, "model": _PROVIDER_MODEL["worker"](p)}
    return out


@router.get("/methodology")
def methodology(founder_id: str | None = None):
    provider = llm.provider() or "anthropic"
    result = {
        "signal": {
            "name": "Founder Score (\"Signal\")",
            "what_it_is": ("A persistent, cross-application score that lives in Memory and "
                          "never resets — one INPUT into the per-opportunity Founder axis, "
                          "not a substitute for it. Computed mechanically from evidence "
                          "already in Memory; no LLM call."),
            "formula": ("weighted mean over the ASSESSED dimensions only, renormalized "
                       "(an unassessed dimension is skipped, not scored as zero)"),
            "weights": founder_score.WEIGHTS,
            "dimensions": {
                "execution_velocity": "min(6, commits_6w×6/60) + min(4, active_days×4/30), from GitHub commit-velocity signals — saturates at 60 commits / 30 active days over a 6-week window.",
                "community_pull": "min(10, 3×log₁₀(1 + max stars/points seen)) — logarithmic so one viral post doesn't dominate.",
                "domain_breadth": "min(10, 2 + 2×distinct outbound sources) — GitHub/HN/arXiv/ProductHunt/YC each count once.",
                "integrity": "10×(1 − contradicted_claims / total_claims) — caps hard on any contradicted claim.",
                "verified_depth": "10×(corroborated_claims / total_claims) — keeps the score from collapsing to integrity alone once a founder has claims to check.",
            },
        },
        "coverage": {
            "name": "Coverage",
            "what_it_is": ("Fraction of the record's informational areas with ≥1 claim — "
                          "evidenced or contradicted both count as \"covered\"; only a "
                          "missing area doesn't. Deliberately never blended with Signal: a "
                          "high-Signal, low-Coverage founder is the cold-start case, not a "
                          "weak one."),
            "formula": f"evidenced areas / {len(founder_score.COVERAGE_AREAS)}",
            "areas": [a[0] for a in founder_score.COVERAGE_AREAS],
        },
        "axes": {
            "name": "3-axis screen (Founder / Market / Idea-vs-Market)",
            "what_it_is": ("NOT mechanical — an LLM judgment against the fund thesis lens, "
                          "run once per founder per thesis. The three axes are stored and "
                          "shown independently and are NEVER averaged into one number; the "
                          "disagreement between them is itself the signal. A first-pass kill "
                          "screen runs first and can stop a clearly non-viable opportunity "
                          "before the three axes are scored at all."),
            "provider": provider,
            "kill_screen": {
                "rubric": promptlib.load_prompt("screen_first_pass",
                    "first-pass kill screen — removes CLEARLY non-viable opportunities"),
                "model": _PROVIDER_MODEL["screen"](provider),
            },
            "rubrics": _axis_methodology(),
        },
        "trust": {
            "name": "Trust Score (per claim)",
            "what_it_is": ("Every claim in the ledger carries its own trust score — never "
                          "one number for the whole company. Uncontested claims get the "
                          "rubric value below by corroboration tier. Contested claims "
                          "(contradicted / self-reported) go to a prosecutor→defender→judge "
                          "adjudication debate whose verdict OVERRIDES the rubric."),
            "rubric": TRUST_RUBRIC,
            "contested_tiers": sorted(CONTESTED_TIERS),
            "tier_definitions": _TIER_DEFS,
        },
    }

    if founder_id:
        conn = db.connect()
        db.init_db(conn)
        founder = conn.execute("SELECT 1 FROM founders WHERE id=?", (founder_id,)).fetchone()
        if not founder:
            raise HTTPException(404, f"unknown founder {founder_id}")
        claims = ingest.get_claims(conn, founder_id)
        signals = founder_score._signals(conn, founder_id)
        dims, dim_notes = founder_score.dimensions_explained(signals, claims)
        cov, areas = founder_score.coverage_explained(claims)
        assessed = {k: v for k, v in dims.items() if v is not None}
        total_w = sum(founder_score.WEIGHTS[k] for k in assessed) or None
        result["for_founder"] = {
            "founder_id": founder_id,
            "signal": {
                "value": founder_score.composite(dims),
                "dimensions": [
                    {"name": k, "value": v, "weight": founder_score.WEIGHTS[k],
                     "assessed": v is not None,
                     "renormalized_weight": (round(founder_score.WEIGHTS[k] / total_w, 3)
                                             if total_w and v is not None else None),
                     "derivation": dim_notes.get(k)}
                    for k, v in dims.items()
                ],
            },
            "coverage": {"value": cov, "areas": areas},
            "claim_count": len(claims),
            "signal_count": len(signals),
        }
    return result
