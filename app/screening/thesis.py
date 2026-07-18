"""Thesis Engine (spec §2.5). A YAML fund config applied twice: as a filter on
sourcing and as a scoring lens in screening. Same founder pool, different config,
different answer (brief FAQ 15)."""
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Thesis:
    name: str
    sectors: list[str] = field(default_factory=list)
    stage: str = ""
    geography: list[str] = field(default_factory=list)
    check_size_usd: int = 0
    ownership_target_pct: float = 0.0
    risk_appetite: str = "medium"
    topics: list[str] = field(default_factory=list)


def load_thesis(path: str | Path) -> Thesis:
    data = yaml.safe_load(Path(path).read_text())
    return Thesis(**data)


def sourcing_topics(thesis: Thesis) -> list[str]:
    """Filter lens on the outbound scanner — which topics/queries to scan."""
    return thesis.topics


def lens(thesis: Thesis) -> str:
    """Text injected into every axis prompt so each rationale references the thesis."""
    return (f"Fund thesis: {thesis.name}. Sectors {thesis.sectors}, stage {thesis.stage}, "
            f"geography {thesis.geography}, check ${thesis.check_size_usd:,}, "
            f"ownership target {thesis.ownership_target_pct}%, "
            f"risk appetite {thesis.risk_appetite}. Score through this lens and reference "
            f"it explicitly in your rationale (e.g. how stage/risk-appetite changes the read).")
