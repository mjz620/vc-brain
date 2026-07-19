"""Decision-layer debate (spec §2.5).

Bull argues invest, Bear (the red-team, seeing the bull case) argues pass — both citing
ONLY existing claim ids — then a Judge emits the recommendation + "what would change our
mind" + open items. The mechanical validator polices every turn: a turn citing a
non-existent claim id is flagged, so the debate can only recombine grounded evidence.
"""
import re

from .. import llm
from ..promptlib import load_prompt
from . import validate
from .schemas import Argument, Recommendation

# The integrity gate in prompts/debate_judge.md fires on contradicted-tier claims that
# are the FOUNDER'S OWN assertions — biography, exit, timeline, traction. Risk-axis
# claims are hypotheses someone raised; one being disproved is not a founder integrity
# failure, and the prompt excludes them explicitly.
_FOUNDER_ASSERTION_AXES = ("founder", "traction")
_ALL_TIERS = ("corroborated", "single_source", "self_reported", "contradicted")
_GATE_LANGUAGE = re.compile(r"integrity gate|contradicted|contradiction", re.I)

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


def integrity_gate_count(claims) -> int:
    """Contradicted-tier claims that are the founder's own assertions. This is the
    integrity gate's ONLY input, and it is fully determined by the ledger — so it is
    computed here rather than left to the judge to tally."""
    return sum(1 for c in claims if c.corroboration == "contradicted"
               and c.axis in _FOUNDER_ASSERTION_AXES)


def _ledger_brief(claims) -> str:
    tiers = {t: 0 for t in _ALL_TIERS}  # every tier, including the zeros
    for c in claims:
        tiers[c.corroboration] = tiers.get(c.corroboration, 0) + 1
    counts = ", ".join(f"{k}={tiers[k]}" for k in _ALL_TIERS)
    # Zero-count tiers were previously omitted entirely, so on a ledger with no
    # contradicted claims the word "contradicted" never reached the judge — and it
    # confabulated the count it had been told to read. State the gate's verdict
    # outright rather than leaving it to be inferred.
    n = integrity_gate_count(claims)
    gate = (f"Integrity-gate input: contradicted founder-assertion claims = {n}. "
            + ("THE INTEGRITY GATE CANNOT FIRE. No claim in this ledger carries the "
               "contradicted tier. Any rationale asserting a contradiction or an "
               "integrity failure is factually false — do not write one."
               if n == 0 else
               "The integrity gate is available; cite the contradicted ids by name."))
    return (f"Mechanical tier counts: {counts}\n{gate}\n" +
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
    system = load_prompt("debate_judge", _JUDGE)
    rec = llm.call("synth", system, judge_prompt, Recommendation,
                   replay=replay, max_tokens=800)

    # The gate's input is mechanical, so a pass justified by an integrity failure the
    # ledger does not contain is wrong by construction — not a judgement call. The
    # prompt already forbids this and the model does it anyway, so it is enforced here
    # instead. Structural passes (no market, no product) never mention contradictions
    # and are left alone.
    n = integrity_gate_count(claims)
    if _phantom_gate(rec, n):
        rec = llm.call(
            "synth", system,
            f"{judge_prompt}\n\n--- MECHANICAL CORRECTION ---\n"
            f"A previous attempt passed citing an integrity failure. The ledger "
            f"contains {n} contradicted founder-assertion claims. The integrity gate "
            f"cannot fire. Re-decide under rules 2-4 only.",
            Recommendation, replay=replay, max_tokens=800)
        if _phantom_gate(rec, n):
            # Mirrors _turn()'s validator note: never silently ship the bad claim.
            rec.rationale += (f" [validator: rationale asserts a contradiction, but the "
                              f"ledger holds {n} contradicted founder-assertion claims — "
                              f"the integrity gate did not fire]")
    return rec, bull, bear


def _phantom_gate(rec, n_contradicted: int) -> bool:
    """A pass whose rationale leans on contradictions that are not in the ledger."""
    return (n_contradicted == 0 and rec.decision == "pass"
            and bool(_GATE_LANGUAGE.search(rec.rationale)))
