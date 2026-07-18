"""FastAPI backend: JSON endpoints over Memory + serves the built React bundle.

No LLM calls except the optional NL-query endpoint (cached). Read-only over vc_brain.db.
"""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, instrument
from .decision import decision as dec
from .memory import db, founder_score, ingest
from .screening import axes as axes_mod
from .screening import thesis as thesis_mod

app = FastAPI(title="VC Brain")
_DIST = config.ROOT / "frontend" / "dist"


def _conn():
    c = db.connect()
    db.init_db(c)
    return c


def _thesis(name: str | None):
    path = config.ROOT / (name or "config/thesis_preseed_ai_infra.yaml")
    if not path.exists():
        raise HTTPException(404, "thesis not found")
    return thesis_mod.load_thesis(path)


def _source_of(conn, founder_id: str) -> str:
    row = conn.execute(
        "SELECT s.source FROM signals s LEFT JOIN resolutions r ON r.signal_id=s.id "
        "WHERE (s.founder_id=? OR r.founder_id=?) ORDER BY s.source LIMIT 1",
        (founder_id, founder_id)).fetchone()
    return row["source"] if row else "unknown"


@app.get("/api/theses")
def theses():
    out = []
    for p in sorted((config.ROOT / "config").glob("thesis_*.yaml")):
        t = thesis_mod.load_thesis(p)
        out.append({"file": f"config/{p.name}", "name": t.name})
    return out


@app.get("/api/founders")
def founders(thesis: str | None = None):
    conn = _conn()
    t = _thesis(thesis)
    ids = [r["fid"] for r in conn.execute(
        "SELECT DISTINCT founder_id fid FROM axis_scores").fetchall()]
    out = []
    for fid in ids:
        name = conn.execute("SELECT name FROM founders WHERE id=?", (fid,)).fetchone()
        axes = dec.per_axis(conn, fid, t.name)  # thesis lens actually applied
        has_memo = conn.execute("SELECT 1 FROM memos WHERE founder_id=? LIMIT 1",
                                (fid,)).fetchone() is not None
        lat = instrument.latency_strip(conn, fid)
        # Signal / Coverage split (spec §3): Signal = persistent Founder Score
        # (evidence-derived, deterministic); Coverage = fraction of the record's
        # informational areas with >=1 claim. NOT derived from the 3 axes.
        cur = founder_score.compute(conn, fid)
        st = founder_score.stored(conn, fid)
        out.append({"id": fid, "name": name["name"] if name else fid,
                    "source": _source_of(conn, fid), "axes": axes,
                    "signal": cur["score"], "coverage": cur["coverage"],
                    "score_history_points": len(st["history"]) if st else 0,
                    "has_memo": has_memo, "latency_total": lat["total_seconds"]})
    # rank by Founder Score desc (unblended axes stay separate in the payload)
    out.sort(key=lambda f: f["signal"] or 0, reverse=True)
    return out


@app.get("/api/founders/{founder_id}")
def founder(founder_id: str, thesis: str | None = None):
    conn = _conn()
    t = _thesis(thesis)
    brief = dec.build(conn, founder_id, t)
    claims = [c.model_dump() for c in ingest.get_claims(conn, founder_id)]
    brief["claims"] = claims  # for click-to-evidence
    return brief


@app.get("/api/sourcing")
def sourcing(thesis: str | None = None):
    """Ranked outbound feed: every resolved founder (screened or not), ranked by
    thesis-topic match + signal count. Includes the drop-log tally — 'nothing
    discarded' rendered as a feature."""
    conn = _conn()
    t = _thesis(thesis)
    rows = conn.execute(
        "SELECT r.founder_id fid, COUNT(*) n, GROUP_CONCAT(DISTINCT s.source) sources, "
        "MAX(COALESCE(s.observed_at, s.ingested_at)) latest, "
        "GROUP_CONCAT(s.content, '\n') blob "
        "FROM resolutions r JOIN signals s ON s.id = r.signal_id "
        "GROUP BY r.founder_id").fetchall()
    screened = {r["fid"] for r in conn.execute(
        "SELECT DISTINCT founder_id fid FROM axis_scores").fetchall()}
    outreach = {r["fid"] for r in conn.execute(
        "SELECT DISTINCT founder_id fid FROM outreach").fetchall()}
    out = []
    for r in rows:
        f = conn.execute("SELECT name, entity_keys FROM founders WHERE id=?",
                         (r["fid"],)).fetchone()
        blob = (r["blob"] or "").lower()
        topic_match = sum(1 for tp in t.topics if tp.lower() in blob)
        cur = founder_score.compute(conn, r["fid"])
        out.append({"id": r["fid"], "name": f["name"] if f else r["fid"],
                    "signal": cur["score"], "coverage": cur["coverage"],
                    "dimensions": cur["dimensions"],
                    "entity_keys": json.loads(f["entity_keys"]) if f else {},
                    "sources": (r["sources"] or "").split(","),
                    "signal_count": r["n"], "latest_signal_at": r["latest"],
                    "thesis_topic_match": topic_match,
                    "screened": r["fid"] in screened,
                    "has_outreach": r["fid"] in outreach})
    out.sort(key=lambda x: (x["thesis_topic_match"], x["signal_count"]), reverse=True)
    dropped = conn.execute(
        "SELECT COUNT(DISTINCT signal_id) c FROM droplog").fetchone()["c"]
    return {"thesis": t.name, "founders": out, "droplog_count": dropped}


@app.get("/api/channels")
def channels():
    """Sourcing-graph lite (stretch 3): per-channel yield through the funnel —
    signals -> resolved -> founders -> screened. Suggestion is a labeled heuristic,
    not learned (no funded-outcome data exists; anything else would be fabricated)."""
    conn = _conn()
    rows = conn.execute(
        "SELECT s.source, COUNT(*) signals, COUNT(r.signal_id) resolved, "
        "COUNT(DISTINCT r.founder_id) founders "
        "FROM signals s LEFT JOIN resolutions r ON r.signal_id = s.id "
        "GROUP BY s.source").fetchall()
    screened = {r["fid"] for r in conn.execute(
        "SELECT DISTINCT founder_id fid FROM axis_scores").fetchall()}
    chans = []
    for r in rows:
        fids = [x["fid"] for x in conn.execute(
            "SELECT DISTINCT r.founder_id fid FROM resolutions r "
            "JOIN signals s ON s.id = r.signal_id WHERE s.source=?",
            (r["source"],)).fetchall()]
        chans.append({"source": r["source"], "signals": r["signals"],
                      "resolved": r["resolved"], "founders": r["founders"],
                      "screened": sum(1 for f in fids if f in screened),
                      "resolve_rate": round(r["resolved"] / r["signals"], 2)
                      if r["signals"] else 0})
    suggestion = None
    scannable = [c for c in chans if c["source"] not in ("deck", "manual", "web")]
    if len(scannable) >= 2:
        med = sorted(c["signals"] for c in scannable)[len(scannable) // 2]
        under = [c for c in scannable if c["signals"] <= med and c["resolve_rate"] > 0]
        if under:
            best = max(under, key=lambda c: c["resolve_rate"])
            suggestion = (f"underexplored channel: '{best['source']}' resolves "
                          f"{best['resolve_rate']:.0%} of signals but has only "
                          f"{best['signals']} scanned — scan it deeper "
                          f"(heuristic on resolve-rate; no outcome data yet)")
    return {"channels": chans, "suggestion": suggestion}


@app.get("/api/query")
def nl_query(q: str):
    """Multi-attribute NL query (MVP 3): one cached model call parses; Memory filters.
    Non-evaluable criteria are flagged and ignored, never guessed."""
    from . import query as query_mod
    conn = _conn()
    try:
        return query_mod.run(conn, q, replay=config.replay_enabled(None))
    except Exception as e:  # replay miss on an unseeded query, or no key
        raise HTTPException(422, f"query could not run: {type(e).__name__}: {e}")


@app.get("/api/trace/{founder_id}/{claim_id}")
def trace(founder_id: str, claim_id: str):
    """Agentic Traceability (stretch 1): the full chain behind one claim —
    claim -> evidence -> source signals -> how trust was set (rubric or the
    prosecutor/defender/judge transcript that overrode it)."""
    conn = _conn()
    row = conn.execute("SELECT * FROM claims WHERE founder_id=? AND claim_id=?",
                       (founder_id, claim_id)).fetchone()
    if not row:
        raise HTTPException(404, "claim not found")
    sig_ids = json.loads(row["signal_ids"] or "[]")
    marks = ",".join("?" * len(sig_ids)) or "''"
    sigs = conn.execute(
        f"SELECT * FROM signals WHERE id IN ({marks}) OR source_url = ?",
        (*sig_ids, row["source_url"])).fetchall()
    adj = conn.execute(
        "SELECT * FROM adjudications WHERE founder_id=? AND claim_id=? "
        "ORDER BY decided_at DESC LIMIT 1", (founder_id, claim_id)).fetchone()
    from .diligence.ledger import rubric_trust
    return {
        "claim": {"id": row["claim_id"], "axis": row["axis"], "text": row["text"],
                  "stance": row["stance"], "evidence": row["evidence"],
                  "source_url": row["source_url"], "source_type": row["source_type"],
                  "corroboration": row["corroboration"], "trust": row["trust"],
                  "observed_at": row["observed_at"]},
        "signals": [{"id": s["id"], "source": s["source"],
                     "source_url": s["source_url"], "content": s["content"],
                     "observed_at": s["observed_at"], "ingested_at": s["ingested_at"]}
                    for s in sigs],
        "rubric_trust": rubric_trust(row["corroboration"]),
        "adjudication": {
            "prosecution": adj["prosecution"], "defense": adj["defense"],
            "corroboration": adj["corroboration"], "trust": adj["trust"],
            "rationale": adj["rationale"], "decided_at": adj["decided_at"],
        } if adj else None,
    }


class Application(BaseModel):
    company: str
    deck_text: str


@app.post("/api/apply")
def apply(body: Application):
    """Inbound intake (MVP 4): deck + company name is the minimum bar. The deck
    lands as a self-reported signal in the same funnel as outbound."""
    import re as _re

    from .memory.models import Founder, Signal
    if not body.company.strip() or not body.deck_text.strip():
        raise HTTPException(422, "company and deck_text are required — nothing else is")
    conn = _conn()
    fid = "founder-" + _re.sub(r"[^a-z0-9]+", "-", body.company.lower()).strip("-")
    ingest.upsert_founder(conn, Founder(id=fid, name=body.company))
    sid, inserted = ingest.ingest_signal(conn, Signal(
        source="deck", source_url=f"application://{fid}", content=body.deck_text,
        observed_at=config.DEMO_TODAY, founder_id=fid))
    from . import llm as llm_mod
    screened = False
    if llm_mod.provider() is not None or config.replay_enabled(None):
        try:
            from .screening import axes as axes_mod
            axes_mod.screen(conn, fid, _thesis(None),
                            replay=config.replay_enabled(None))
            screened = True
        except Exception:
            pass  # screening is best-effort at intake; the founder is stored either way
    return {"founder_id": fid, "signal_id": sid, "duplicate": not inserted,
            "screened": screened}


@app.get("/api/outreach/{founder_id}")
def outreach(founder_id: str):
    conn = _conn()
    rows = conn.execute(
        "SELECT o.*, s.source_url, s.content FROM outreach o "
        "JOIN signals s ON s.id = o.signal_id WHERE o.founder_id=?",
        (founder_id,)).fetchall()
    return [{"subject": r["subject"], "body": r["body"],
             "created_at": r["created_at"], "triggering_signal_url": r["source_url"],
             "triggering_signal": r["content"]} for r in rows]


@app.post("/api/activate/{founder_id}")
def activate_founder(founder_id: str, thesis: str | None = None):
    """Draft Activate outreach citing the triggering signal (cached => replay-safe)."""
    from . import activate as activate_mod
    from . import llm as llm_mod
    conn = _conn()
    t = _thesis(thesis)
    if llm_mod.provider() is None and not config.replay_enabled(None):
        raise HTTPException(409, "no LLM key and not in replay — cannot draft")
    try:
        d = activate_mod.draft(conn, founder_id, t.name,
                               replay=config.replay_enabled(None))
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"subject": d.subject, "body": d.body,
            "cited_signal_url": d.cited_signal_url}


class ThesisConfig(BaseModel):
    name: str
    sectors: list[str]
    stage: str
    geography: list[str]
    check_size_usd: int
    ownership_target_pct: float
    risk_appetite: str
    topics: list[str]


@app.post("/api/thesis")
def save_thesis(body: ThesisConfig):
    """Thesis Engine is configurable (brief FAQ 15): persist an investor-edited
    thesis as a YAML config next to the built-ins."""
    import re as _re

    import yaml
    slug = _re.sub(r"[^a-z0-9]+", "_", body.name.lower()).strip("_") or "custom"
    path = config.ROOT / "config" / f"thesis_{slug}.yaml"
    path.write_text(yaml.safe_dump(body.model_dump(), sort_keys=False))
    return {"file": f"config/{path.name}", "name": body.name}


@app.get("/api/killed")
def killed():
    conn = _conn()
    rows = conn.execute("SELECT founder_id, reason FROM kill_log GROUP BY founder_id").fetchall()
    return [{"id": r["founder_id"], "reason": r["reason"]} for r in rows]


# --- static SPA (built bundle) ---
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(_DIST / "index.html")
