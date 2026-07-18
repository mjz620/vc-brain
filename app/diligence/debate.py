"""Decision-layer debate (spec §2.5).

Bull argues invest, Bear (the red-team, seeing the bull case) argues pass — both citing
ONLY existing claim ids — then a Judge emits the recommendation + "what would change our
mind" + open items. The mechanical validator polices every turn: a turn citing a
non-existent claim id is flagged, so the debate can only recombine grounded evidence.
"""
from .. import llm
from ..promptlib import load_prompt
from . import validate
from .schemas import Argument, Recommendation

_BULL = ("You are the bull. Make the strongest case to INVEST $100K, citing specific claim "
         "ids in [brackets]. Only cite claim ids that exist in the ledger.")
_BEAR = ("You are the bear / red-team. Given the bull case, make the strongest case to PASS "
         "or to condition the investment — lead with any contradicted or unverified claims. "
         "Cite claim ids in [brackets]; only cite ids that exist in the ledger.")
_JUDGE = ("You are the investment judge. Given the ledger, the bull case, and the bear case, "
          "decide: invest / pass / conditional, the $ amount (100000 for pre-seed), the 2-3 "
          "claim ids the decision turns on, one 'what would change our mind' line, the open "
          "due-diligence items, and a rationale. If the two most impressive claims are the "
          "two that fail verification, that caps the founder axis — pass.")


def _ledger_brief(claims) -> str:
    tiers: dict[str, int] = {}
    for c in claims:
        tiers[c.corroboration] = tiers.get(c.corroboration, 0) + 1
    counts = ", ".join(f"{k}={v}" for k, v in sorted(tiers.items()))
    return (f"Mechanical tier counts: {counts}\n" +
            "\n".join(f"[{c.id}] {c.axis} · trust {c.trust:.2f} · {c.corroboration} · "
                      f"{c.stance}: {c.text}" for c in claims))


def _turn(name, default, prompt, valid_ids, *, replay) -> str:
    arg = llm.call("worker", load_prompt(name, default), prompt, Argument,
                   replay=replay, max_tokens=700).argument
    v = validate.validate_turn(arg, valid_ids)
    if v.unknown_ids:
        arg += f"\n[validator: ignored non-existent claim ids {v.unknown_ids}]"
    return arg


def run_debate(claims, thesis_lens: str, *, replay: bool):
    """Bull -> Bear -> Judge. Returns (Recommendation, bull_text, bear_text)."""
    valid_ids = {c.id for c in claims}
    brief = f"{thesis_lens}\n\n--- Claim ledger ---\n{_ledger_brief(claims)}"
    bull = _turn("debate_bull", _BULL, brief, valid_ids, replay=replay)
    bear = _turn("debate_bear", _BEAR, brief + f"\n\n--- Bull case ---\n{bull}",
                 valid_ids, replay=replay)
    judge_prompt = f"{brief}\n\n--- Bull ---\n{bull}\n\n--- Bear ---\n{bear}"
    rec = llm.call("synth", load_prompt("debate_judge", _JUDGE), judge_prompt,
                   Recommendation, replay=replay, max_tokens=800)
    return rec, bull, bear
