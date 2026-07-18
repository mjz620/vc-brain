"""Pydantic schemas for the Memory layer.

`Claim` is the ledger schema (spec §4) and is the structured-output target on every
diligence worker call. `Signal` is a raw ingested event (append-only). `Founder` is
the canonical person record; its score carries an append-only history so the trend
over time falls out for free (spec §2.1).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Source = Literal["github", "hn", "arxiv", "producthunt", "deck", "web", "manual"]


class Claim(BaseModel):
    """One evidence-tagged assertion in the ledger. Spec §4, verbatim fields.

    A negative result is a first-class claim: e.g. stance="contradicts",
    source_type="web", evidence="EDGAR search for DataLoom Form D: no filing found",
    source_url=<the search URL>. Nothing about gaps is left implicit.
    """

    id: str  # e.g. "team-03"
    axis: Literal["founder", "market", "idea", "traction", "risk"]
    text: str
    stance: Literal["supports", "contradicts", "neutral"]
    evidence: str  # snippet
    source_url: str
    source_type: Literal["deck", "web", "github", "hn", "arxiv", "inferred", "unavailable"]
    corroboration: Literal["self_reported", "single_source", "corroborated", "contradicted"]
    trust: float  # 0–1, rubric-anchored
    observed_at: str | None = None


class Signal(BaseModel):
    """A raw ingested event. Append-only; nothing discarded (brief requirement)."""

    source: Source
    source_url: str
    content: str
    observed_at: str | None = None
    founder_id: str | None = None  # nullable until entity resolution attaches it


class ScoreEntry(BaseModel):
    """One point in a founder's score history."""

    timestamp: str
    score: float
    trigger: str


class FounderScore(BaseModel):
    """Persistent Founder Score. `dimensions` + `coverage` are the current snapshot;
    `history` is append-only so re-running the pipeline appends, never overwrites."""

    dimensions: dict[str, float] = Field(default_factory=dict)
    coverage: float = 0.0
    history: list[ScoreEntry] = Field(default_factory=list)


class Founder(BaseModel):
    """Canonical person record. Persists across applications, never resets."""

    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    entity_keys: dict[str, str] = Field(default_factory=dict)  # github, hn, arxiv, domain
    founder_score: FounderScore = Field(default_factory=FounderScore)
    first_seen: str | None = None
    last_updated: str | None = None
