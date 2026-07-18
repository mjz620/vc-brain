"""Grounding guard + critic (spec §2.4): mechanical validator first, then one LLM
revision round if it flags anything (fake claim ids or uncited quantitative claims)."""
from .. import llm
from ..promptlib import load_prompt
from . import validate
from .schemas import CriticResult

_DEFAULT = ("You are a memo critic enforcing evidence discipline. Given a memo, the "
            "validator's issues, and the list of valid claim ids, return a revised memo "
            "that: removes or replaces every non-existent claim id; ensures every "
            "quantitative sentence cites a real id OR is an explicit gap flag ('not "
            "disclosed'); and preserves the contradiction-first structure. Change nothing "
            "else.")


def finalize(memo: str, valid_ids, *, replay: bool):
    """Return (final_memo, Violations). Max one LLM revision round."""
    v = validate.validate(memo, valid_ids)
    if v.ok:
        return memo, v
    user = (f"--- Memo ---\n{memo}\n\n--- Validator issues ---\n"
            f"non-existent claim ids cited: {v.unknown_ids}\n"
            f"uncited quantitative sentences: {v.uncited_quant}\n\n"
            f"Valid claim ids: {sorted(valid_ids)}\n\nReturn the corrected memo.")
    res = llm.call("critic", load_prompt("critic", _DEFAULT), user, CriticResult,
                   replay=replay, max_tokens=3500)
    revised = res.revised_markdown or memo
    return revised, validate.validate(revised, valid_ids)
