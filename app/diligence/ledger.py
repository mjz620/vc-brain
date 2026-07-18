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
    return Claim(id=draft.id, axis=draft.axis, text=draft.text, stance=draft.stance,
                 evidence=draft.evidence, source_url=draft.source_url,
                 source_type=draft.source_type, corroboration=draft.corroboration,
                 trust=rubric_trust(draft.corroboration), observed_at=draft.observed_at)


def is_contested(claim: Claim) -> bool:
    return claim.corroboration in CONTESTED_TIERS


def assemble(drafts: list[ClaimDraft]) -> list[Claim]:
    return [to_claim(d) for d in drafts]
