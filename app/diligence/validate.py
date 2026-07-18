"""Mechanical grounding guard (no LLM).

Two checks, run on every debate turn AND the final memo:
  1. unknown_citations — any [claim-id ...] citation that isn't a real ledger claim /
     open item. This is what makes the debate structurally incapable of hallucinating:
     a turn or sentence citing a non-existent claim id is rejected outright.
  2. uncited_quant — a quantitative assertion (has a number/$/%) with no citation and
     not a gap flag. Enforces the "every factual sentence cites >=1 claim id" constraint
     at high precision; the LLM critic handles softer semantic support afterwards.
"""
import re

from pydantic import BaseModel

# [team-02] or [team-02 · 0.9 · corr] or [dd-03 · 0.85 · corr — EDGAR ...]
_CITATION = re.compile(r"\[([a-z]{2,5}-\d{1,3})(?:[^\]]*)?\]")
_QUANT = re.compile(r"[\d$%]")
_GAP = re.compile(r"not disclosed|not applicable|unavailable|n/?a\b|not derivable|"
                  r"not yet|no external corroboration|negative result", re.I)


class Violations(BaseModel):
    unknown_ids: list[str] = []       # cited but not in the valid set — HARD failure
    uncited_quant: list[str] = []     # quantitative assertion with no citation — advisory

    @property
    def ok(self) -> bool:
        # The hard grounding guarantee is citation existence: no memo/turn may cite a
        # claim id that isn't in the ledger. uncited_quant is an advisory signal the
        # synthesizer prompt + LLM critic address; it does not by itself fail the memo.
        return not self.unknown_ids


def citations(text: str) -> set[str]:
    return {m.group(1) for m in _CITATION.finditer(text)}


def unknown_citations(text: str, valid_ids) -> list[str]:
    return sorted(citations(text) - set(valid_ids))


def _sentences(text: str) -> list[str]:
    # split on sentence enders and newlines/bullets; keep it simple and mechanical
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


_STRUCTURAL = re.compile(r"^([#\-*>]|\d+[.)]|\*\*)")  # headings, list markers, bold labels


def uncited_quant_sentences(text: str) -> list[str]:
    out = []
    for s in _sentences(text):
        st = s.strip()
        if not st or _CITATION.search(st) or _STRUCTURAL.match(st):
            continue
        if len(st.split()) < 6:  # short label/field lines (e.g. "Amount: $100,000")
            continue
        if _QUANT.search(st) and not _GAP.search(st):
            out.append(st)
    return out


def validate(text: str, valid_ids) -> Violations:
    """Full validation for a memo (citation existence + uncited quantitative claims)."""
    return Violations(unknown_ids=unknown_citations(text, valid_ids),
                      uncited_quant=uncited_quant_sentences(text))


def validate_turn(text: str, valid_ids) -> Violations:
    """Lighter check for a debate turn: only citation existence (turns argue, they don't
    have to cite a claim in every sentence)."""
    return Violations(unknown_ids=unknown_citations(text, valid_ids))
