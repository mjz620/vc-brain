"""Structured-output schemas for the diligence pipeline (provider-agnostic parse)."""
from typing import Literal

from pydantic import BaseModel


class ClaimDraft(BaseModel):
    """A worker-extracted claim. Trust is NOT set here — it's derived by the ledger
    (rubric) or the adjudication Judge (contested). corroboration is the worker's read."""
    id: str
    axis: Literal["founder", "market", "idea", "traction", "risk"]
    text: str
    stance: Literal["supports", "contradicts", "neutral"]
    evidence: str
    source_url: str
    source_type: Literal["deck", "web", "github", "hn", "arxiv", "tavily", "inferred"]
    corroboration: Literal["self_reported", "single_source", "corroborated", "contradicted"]
    observed_at: str | None


class WorkerOutput(BaseModel):
    claims: list[ClaimDraft]


class Verdict(BaseModel):
    """Adjudication Judge's decision on a contested claim."""
    corroboration: Literal["self_reported", "single_source", "corroborated", "contradicted"]
    trust: float
    stance: Literal["supports", "contradicts", "neutral"]
    rationale: str


class Argument(BaseModel):
    """One debate turn (prosecutor/defender/bull/bear). Must cite claim ids in brackets."""
    argument: str


class Recommendation(BaseModel):
    decision: Literal["invest", "pass", "conditional"]
    amount_usd: int
    claims_it_turns_on: list[str]          # the 2-3 claim ids the decision hinges on
    what_would_change_our_mind: str
    open_items: list[str]
    rationale: str


class MemoOut(BaseModel):
    markdown: str


class CriticResult(BaseModel):
    supported: bool
    issues: list[str]
    revised_markdown: str
