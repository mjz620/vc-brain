"""Structured-output schemas for the diligence pipeline (provider-agnostic parse)."""
from typing import Literal

from pydantic import BaseModel, Field


class ClaimDraft(BaseModel):
    """A worker-extracted claim. Trust is NOT set here — it's derived by the ledger
    (rubric) or the adjudication Judge (contested). corroboration is the worker's read."""
    id: str
    # The attribution instruction lives HERE, in the schema, not in prompts/ — those
    # files are human-owned. A company has one founder_id but may have several people,
    # so without an explicit subject the extractor hangs one co-founder's evidence on
    # another and the adjudicator then correctly reports a contradiction that the
    # pipeline itself manufactured.
    subject: str | None = Field(
        default=None,
        description=(
            "The exact full name of the person this claim is about, copied from the "
            "evidence. Use null ONLY when the claim is about the company rather than a "
            "specific person. When the evidence names several founders, attribute each "
            "claim to the one the evidence actually supports — never merge two people, "
            "and never attach one person's GitHub, education, or employment to another."))
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


class AskAnswer(BaseModel):
    """Grounded Q&A over the claim ledger. Refusal is a first-class outcome."""
    answer: str
    cited_claim_ids: list[str]
    refused: bool
