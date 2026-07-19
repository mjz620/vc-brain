"""Data-quality endpoints (owned by the data-integrity workstream).

Everything is computed at request time from the DB — no derived tables, so the
panel can never disagree with the underlying signals/resolutions/droplog rows.
"""
import json

from fastapi import APIRouter

from ..memory import db
from ..memory.resolve import INFRA_DOMAINS

router = APIRouter(prefix="/api")


@router.get("/quality")
def quality():
    conn = db.connect()

    channels: dict[str, dict] = {}
    for r in conn.execute("SELECT source, COUNT(*) n FROM signals GROUP BY source"):
        channels[r["source"]] = {"ingested": r["n"], "resolved": 0,
                                 "distinct_founders": 0, "dropped": 0}
    for r in conn.execute(
            "SELECT s.source, COUNT(*) n, COUNT(DISTINCT r.founder_id) f "
            "FROM resolutions r JOIN signals s ON s.id = r.signal_id "
            "GROUP BY s.source"):
        ch = channels.setdefault(r["source"], {"ingested": 0, "dropped": 0})
        ch["resolved"], ch["distinct_founders"] = r["n"], r["f"]
    for r in conn.execute(
            "SELECT s.source, COUNT(DISTINCT d.signal_id) n FROM droplog d "
            "JOIN signals s ON s.id = d.signal_id GROUP BY s.source"):
        channels.setdefault(r["source"], {})["dropped"] = r["n"]

    drop_reasons = {r["reason"]: r["n"] for r in conn.execute(
        "SELECT reason, COUNT(*) n FROM droplog GROUP BY reason")}
    kill_log = conn.execute("SELECT COUNT(*) c FROM kill_log").fetchone()["c"]
    total_signals = conn.execute("SELECT COUNT(*) c FROM signals").fetchone()["c"]

    ax = channels.get("arxiv", {"ingested": 0, "resolved": 0})
    arxiv_pool = {
        "ingested": ax.get("ingested", 0),
        "resolved": ax.get("resolved", 0),
        "awaiting_second_key": ax.get("ingested", 0) - ax.get("resolved", 0),
        "status": ("arXiv papers usually carry a single identity key (author "
                   "slug), below the 2-key resolution bar; they wait in the pool "
                   "until a second key (e.g. a linked GitHub repo) appears — not "
                   "force-resolved, not discarded."),
    }

    # Audit summary, recomputed live: founders still carrying a blacklisted
    # infra domain as an entity key, and signals unlinked by the audit fix.
    bad = []
    for r in conn.execute("SELECT id, entity_keys FROM founders"):
        keys = json.loads(r["entity_keys"] or "{}")
        if any(v and v.lower() in INFRA_DOMAINS for v in keys.values()):
            bad.append(r["id"])
    audit = {
        "founders_with_blacklisted_keys": bad,
        "unlinked_infra_merge_signals": drop_reasons.get(
            "unlinked: infra-domain merge", 0),
        "infra_domain_drops_at_resolve": drop_reasons.get(
            "infra_domain_not_linking", 0),
    }

    return {
        "channels": channels,
        "drop_reasons": drop_reasons,
        "kill_log": kill_log,
        "dedup_protected_signals": total_signals,
        "arxiv_pool": arxiv_pool,
        "audit": audit,
        "notes": ("dedup_protected_signals is the count of stored signals each "
                  "protected by a dedup hash; dedup rejections themselves are "
                  "not persisted, so no rejection count is reported."),
    }
