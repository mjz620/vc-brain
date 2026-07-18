"""Diligence orchestrator: evidence -> workers -> ledger -> fact-layer adjudication ->
decision-layer debate -> synthesizer -> critic -> stored memo (spec §2.4)."""
import os
from datetime import datetime, timezone

from .. import instrument
from ..memory import founder_score, ingest
from ..screening import thesis as thesis_mod
from . import adjudicate, critic, debate, ledger, loader, synthesizer, workers

# Cost control: adjudicating every contested claim is the main API-credit driver
# (each is a 3-call prosecutor/defender/judge debate). Cap to the most material ones,
# contradicted first — the rest keep their rubric trust. Override with VC_MAX_ADJUDICATIONS.
MAX_ADJUDICATIONS = int(os.environ.get("VC_MAX_ADJUDICATIONS", "6"))
_TIER_RANK = {"contradicted": 0, "self_reported": 1, "single_source": 2, "corroborated": 3}


def _store_memo(conn, founder_id, thesis_name, rec, memo, bull, bear) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO memos (founder_id, thesis, decision, recommendation, "
        "memo_md, bull, bear, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (founder_id, thesis_name, rec.decision, rec.model_dump_json(), memo, bull, bear,
         datetime.now(timezone.utc).isoformat()))
    conn.commit()


def run_diligence(conn, founder_id: str, thesis, *, replay: bool) -> dict:
    lens = thesis_mod.lens(thesis)
    evidence = loader.founder_evidence(conn, founder_id)

    # 1. Workers extract claims (grounded, non-adversarial).
    with instrument.stage(conn, founder_id, "extract"):
        claims = ledger.assemble(workers.extract_all(evidence, replay=replay))
    valid_ids = {c.id for c in claims}
    # Cap adjudication to the most material contested claims (contradicted first).
    contested = sorted((c for c in claims if ledger.is_contested(c)),
                       key=lambda c: _TIER_RANK.get(c.corroboration, 9))[:MAX_ADJUDICATIONS]

    # 2. Fact-layer debate sets the tier/trust on each contested claim (Judge, not rubric).
    with instrument.stage(conn, founder_id, "adjudicate"):
        for c in contested:
            verdict, pros, deff = adjudicate.adjudicate(c, evidence, valid_ids, replay=replay)
            c.corroboration, c.trust, c.stance = (verdict.corroboration, verdict.trust,
                                                  verdict.stance)
            adjudicate.store(conn, founder_id, c.id, pros, deff, verdict)

    # 3. Persist the adjudicated ledger, then append a Founder Score history point —
    # diligence changed the record (integrity + coverage move with the claims).
    for c in claims:
        ingest.store_claim(conn, founder_id, c)
    fs = founder_score.recompute(conn, founder_id, "diligence",
                                 now=datetime.now(timezone.utc).isoformat())
    score_line = (f"Signal {fs['score']} / Coverage {fs['coverage']:.0%}"
                  if fs["score"] is not None else "")

    # 4. Decision-layer debate -> recommendation.
    with instrument.stage(conn, founder_id, "debate"):
        rec, bull, bear = debate.run_debate(claims, lens, replay=replay)

    # 5. Synthesize the memo, then the grounding guard + one critic revision.
    with instrument.stage(conn, founder_id, "synthesize"):
        memo = synthesizer.synthesize(claims, rec, bull, bear, lens,
                                      score_line=score_line, replay=replay)
        memo, viol = critic.finalize(memo, valid_ids, replay=replay)

    _store_memo(conn, founder_id, thesis.name, rec, memo, bull, bear)
    return {"claims": len(claims), "contested": len(contested), "recommendation": rec,
            "memo": memo, "violations": viol}
