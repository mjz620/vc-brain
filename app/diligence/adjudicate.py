"""Fact-layer debate (spec §2.4, brief Validator stretch goal).

For each contested claim: a Prosecutor argues it is false/unverified, a Defender (seeing
the prosecution) argues it holds — both MUST cite the evidence — then a Judge sets the
corroboration tier + Trust Score + stance. Output is a grounded tier, not a new claim.
Every turn is validated: a turn citing a claim id not in the ledger is flagged.
"""
from datetime import datetime, timezone

from .. import llm
from ..promptlib import load_prompt
from . import validate
from .schemas import Argument, Verdict

_PROSECUTOR = ("You are a skeptical diligence prosecutor. Argue that the claim below is "
               "FALSE, unverified, or overstated, citing the evidence and other claim ids "
               "in [brackets]. Be specific about what the record does and does not show.")
_DEFENDER = ("You are the defense. Given the prosecution, argue whether the claim can be "
             "supported, citing the evidence and claim ids in [brackets]. Concede what is "
             "genuinely unverified; do not manufacture support that isn't in the evidence.")
_JUDGE = ("You are the adjudicating judge. Given the claim, the prosecution, and the "
          "defense, decide the corroboration tier (self_reported / single_source / "
          "corroborated / contradicted), a Trust Score 0-1 (self_reported caps at 0.6; a "
          "claim the external record contradicts is 'contradicted' with low trust), the "
          "stance, and a one-line rationale.")


def _turn(system_name, default, prompt, valid_ids, *, replay) -> str:
    system = load_prompt(system_name, default)
    arg = llm.call("worker", system, prompt, Argument, replay=replay, max_tokens=600).argument
    v = validate.validate_turn(arg, valid_ids)
    if v.unknown_ids:  # grounding guard: flag fabricated citations
        arg += f"\n[validator: ignored non-existent claim ids {v.unknown_ids}]"
    return arg


def adjudicate(claim, evidence: str, valid_ids, *, replay: bool):
    """Run prosecutor -> defender -> judge on one contested claim. Returns
    (Verdict, prosecution_text, defense_text)."""
    base = (f"Contested claim [{claim.id}] ({claim.corroboration}): {claim.text}\n"
            f"Evidence snippet: {claim.evidence}\nSource: {claim.evidence_url}\n\n"
            f"--- Full founder evidence ---\n{evidence}")
    prosecution = _turn("adj_prosecutor", _PROSECUTOR, base, valid_ids, replay=replay)
    defense = _turn("adj_defender", _DEFENDER,
                    base + f"\n\n--- Prosecution ---\n{prosecution}", valid_ids, replay=replay)
    judge_prompt = (f"{base}\n\n--- Prosecution ---\n{prosecution}\n\n"
                    f"--- Defense ---\n{defense}")
    # Judge on the cheap tier: the tier/trust decision is well-structured; reserve gpt-4o
    # for the recommendation judge, synthesizer, and critic (cost control).
    verdict = llm.call("worker", load_prompt("adj_judge", _JUDGE), judge_prompt, Verdict,
                       replay=replay, max_tokens=400)
    return verdict, prosecution, defense


def store(conn, founder_id, claim_id, prosecution, defense, verdict) -> None:
    conn.execute(
        "INSERT INTO adjudications (founder_id, claim_id, prosecution, defense, "
        "corroboration, trust, rationale, decided_at) VALUES (?,?,?,?,?,?,?,?)",
        (founder_id, claim_id, prosecution, defense, verdict.corroboration,
         verdict.trust, verdict.rationale, datetime.now(timezone.utc).isoformat()))
    conn.commit()
