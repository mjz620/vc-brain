"""Load a fixture founder's RAW EVIDENCE into Memory (inbound path).

Ingests the deck (deck-summary.txt) as deck signals and the external-verification
signals (signals.jsonl) as web signals. This is raw evidence only — the pipeline
DERIVES claims, trust tiers, and contradictions from it (the fixture's answer-key
cross-reference in profile.md is never fed to the workers).
"""
import json

from .. import config
from ..memory import ingest
from ..memory.models import Founder, Signal

# Fixture dir -> (founder_id, display name). Inbound demo founders.
FIXTURES = {
    "founder_b_corevance": ("founder-corevance", "Devin Marsh / Corevance"),
    "founder_c_parcelmind": ("founder-parcelmind", "Anand & Ohl / Parcelmind"),
}


def load_fixture(conn, fixture: str, *, replay: bool = False) -> str:
    """Ingest a fixture's raw evidence; returns the founder_id."""
    founder_id, name = FIXTURES[fixture]
    fdir = config.FIXTURES / fixture
    ingest.upsert_founder(conn, Founder(id=founder_id, name=name,
                                        entity_keys={"fixture": fixture}))

    deck = fdir / "deck-summary.txt"
    if deck.exists():
        ingest.ingest_signal(conn, Signal(
            source="deck", source_url=f"file://{deck.name}",
            content=deck.read_text(), observed_at=config.DEMO_TODAY,
            founder_id=founder_id))

    jsonl = fdir / "signals.jsonl"
    if jsonl.exists():
        for line in jsonl.read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                ingest.ingest_signal(conn, Signal(founder_id=founder_id, **d))
    return founder_id


def founder_evidence(conn, founder_id: str) -> str:
    """All of a founder's signals as a text block for the diligence workers."""
    rows = conn.execute(
        "SELECT s.source, s.source_url, s.content FROM signals s "
        "LEFT JOIN resolutions r ON r.signal_id = s.id "
        "WHERE s.founder_id = ? OR r.founder_id = ?", (founder_id, founder_id)).fetchall()
    return "\n\n".join(f"[{r['source']}] source_url={r['source_url']}\n{r['content']}"
                       for r in rows)
