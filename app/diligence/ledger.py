"""Ledger assembly + Trust Score.

Trust is rubric-anchored on the corroboration tier (spec §2.4): self_reported caps low,
corroboration raises it, contradiction sinks it. Contested claims (contradicted /
self_reported) are handed to the adjudication Judge, which OVERRIDES the rubric trust.
Uncontested claims keep the fast rubric value.
"""
from ..memory.models import Claim
from .schemas import ClaimDraft

# Rubric: corroboration tier -> trust. self_reported is capped at 0.6 (spec §2.4).
TRUST_RUBRIC = {"self_reported": 0.4, "single_source": 0.6,
                "corroborated": 0.85, "contradicted": 0.3}

# Tiers that get sent to the adjudication debate rather than trusted on the rubric alone.
CONTESTED_TIERS = {"contradicted", "self_reported"}


def rubric_trust(corroboration: str) -> float:
    return TRUST_RUBRIC.get(corroboration, 0.5)


def to_claim(draft: ClaimDraft) -> Claim:
    # ClaimDraft keeps the LLM-facing `source_url` field name (prompt- and
    # cache-key-stable); the ledger Claim stores it as the required evidence_url.
    # Raises ValidationError if the draft carries no resolvable URL.
    return Claim(id=draft.id, subject=draft.subject,
                 axis=draft.axis, text=draft.text, stance=draft.stance,
                 evidence=draft.evidence, evidence_url=draft.source_url,
                 evidence_excerpt=draft.evidence,
                 source_type=draft.source_type, corroboration=draft.corroboration,
                 trust=rubric_trust(draft.corroboration), observed_at=draft.observed_at)


def is_contested(claim: Claim) -> bool:
    return claim.corroboration in CONTESTED_TIERS


def assemble(drafts: list[ClaimDraft]) -> tuple[list[Claim], list[dict]]:
    """Validate drafts into ledger claims. A draft with no resolvable evidence URL
    is dropped and reported — never stored, never given a fabricated URL."""
    claims, dropped = [], []
    for d in drafts:
        try:
            claims.append(to_claim(d))
        except Exception as e:
            dropped.append({"id": d.id, "text": d.text,
                            "reason": f"no resolvable evidence_url ({d.source_url!r})",
                            "detail": str(e)})
    return claims, dropped
