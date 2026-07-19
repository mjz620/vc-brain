"""Evidence-layer endpoints (owned by the evidence/Tavily workstream).

POST /api/enrich/{founder_id} — fetch + ingest Tavily news signals for a founder
(no diligence rerun). Refused for the demo fixture founders: their signals feed
the llm cache keys, so enrichment would break demo determinism.

GET /api/evidence/{founder_id} — the founder's evidence inventory: every claim's
evidence_url/title/excerpt/retrieved_at with its backing signals, plus all
signals grouped by source domain, for the UI's evidence surfacing.
"""
import json

from fastapi import APIRouter, HTTPException

from .. import cache, config
from ..diligence import pipeline
from ..memory import db
from ..sources import tavily
from ..sources.http import domain_of

router = APIRouter(prefix="/api")


@router.post("/enrich/{founder_id}")
def enrich(founder_id: str):
    if founder_id in pipeline.FIXTURE_FOUNDER_IDS:
        raise HTTPException(409, detail=(
            f"{founder_id} is a demo fixture founder — news enrichment is refused "
            "because new signals would change worker evidence and regenerate cached "
            "demo claims (determinism guardrail). Enrich novel founders only."))
    conn = db.connect()
    try:
        found = pipeline.enrich_news(conn, founder_id,
                                     replay=config.replay_enabled())
    except KeyError:
        raise HTTPException(404, detail=f"unknown founder {founder_id}")
    except (RuntimeError, cache.ReplayMiss) as e:
        raise HTTPException(503, detail=f"Tavily unavailable: {e}")
    return {"founder_id": founder_id, "found": found, "spend": tavily.spend_state()}


@router.get("/evidence/{founder_id}")
def evidence_inventory(founder_id: str):
    conn = db.connect()
    if conn.execute("SELECT 1 FROM founders WHERE id = ?",
                    (founder_id,)).fetchone() is None:
        raise HTTPException(404, detail=f"unknown founder {founder_id}")

    sig_rows = conn.execute(
        "SELECT s.id, s.source, s.source_url, s.content, s.observed_at, s.ingested_at "
        "FROM signals s LEFT JOIN resolutions r ON r.signal_id = s.id "
        "WHERE s.founder_id = ? OR r.founder_id = ?",
        (founder_id, founder_id)).fetchall()
    signals = {r["id"]: {"id": r["id"], "source": r["source"],
                         "source_url": r["source_url"],
                         "excerpt": r["content"][:280], "observed_at": r["observed_at"],
                         "ingested_at": r["ingested_at"]} for r in sig_rows}

    by_domain: dict[str, list] = {}
    for s in signals.values():
        by_domain.setdefault(domain_of(s["source_url"]) or s["source"], []).append(s)

    claim_rows = conn.execute(
        "SELECT claim_id, axis, text, stance, evidence, evidence_url, evidence_title, "
        "evidence_excerpt, retrieved_at, source_type, corroboration, trust, signal_ids "
        "FROM claims WHERE founder_id = ?", (founder_id,)).fetchall()
    claims = [{
        "id": r["claim_id"], "axis": r["axis"], "text": r["text"], "stance": r["stance"],
        "evidence_url": r["evidence_url"], "evidence_title": r["evidence_title"],
        "evidence_excerpt": r["evidence_excerpt"] or r["evidence"],
        "retrieved_at": r["retrieved_at"], "source_type": r["source_type"],
        "corroboration": r["corroboration"], "trust": r["trust"],
        "signals": [signals[sid] for sid in json.loads(r["signal_ids"] or "[]")
                    if sid in signals],
    } for r in claim_rows]

    return {"founder_id": founder_id, "claims": claims,
            "signals_by_domain": by_domain}
