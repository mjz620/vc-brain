"""Synthesizer (spec §2.4): writes the memo under the hard constraint that every factual
sentence cites >=1 claim id. Reproduces target-memos.md structure — contradictions first,
recommendation, required sections, DD log, gaps in the brief's own words."""
from .. import llm
from ..promptlib import load_prompt
from .schemas import MemoOut

_DEFAULT = (
    "You write a Bessemer-style investment memo. Sections IN ORDER:\n"
    "1. '## ⚠ Contradictions found — read first' — ONLY if the ledger has contradicted "
    "claims; list each with the claim ids that establish it. Omit the section if none.\n"
    "2. '## Recommendation' — the decision (invest/pass/conditional), $ amount, the 2-3 "
    "claims it turns on, and a 'What would change our mind' line.\n"
    "3. '## Company snapshot'  4. '## Investment hypotheses'  5. '## SWOT'  "
    "6. '## Problem & product'  7. '## Traction & KPIs'  8. '## Due diligence log'.\n"
    "HARD RULES: every sentence making a factual assertion MUST cite >=1 claim id inline, "
    "SUBSTITUTING that claim's actual trust score (2 decimals) and corroboration tier from "
    "the ledger — e.g. [team-02 · 0.90 · corroborated]. Never write the literal words "
    "'trust' or 'tier'. Use ONLY ids present in the ledger. Contradicted claims go at "
    "the very top. Render any missing/withheld data with the brief's phrasing ('not "
    "disclosed', 'not applicable', 'unavailable at this stage') — NEVER invent a value. "
    "Be concise; padding counts against you.")


def _ledger(claims) -> str:
    return "\n".join(f"[{c.id}] {c.axis} · trust {c.trust:.2f} · {c.corroboration} · "
                     f"{c.stance}: {c.text}  (src {c.source_url})" for c in claims)


def synthesize(claims, rec, bull, bear, thesis_lens: str, *, replay: bool) -> str:
    user = (f"{thesis_lens}\n\n--- Claim ledger (cite these ids only) ---\n{_ledger(claims)}\n\n"
            f"--- Recommendation ---\n{rec.model_dump()}\n\n"
            f"--- Bull case ---\n{bull}\n\n--- Bear case ---\n{bear}\n\nWrite the memo.")
    return llm.call("synth", load_prompt("synthesizer", _DEFAULT), user, MemoOut,
                    replay=replay, max_tokens=3500).markdown
