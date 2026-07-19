"""FastAPI backend: JSON endpoints over Memory + serves the built React bundle.

No LLM calls except the optional NL-query endpoint (cached). Read-only over vc_brain.db.
"""
import json
import threading
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, deck_pdf, instrument, ratelimit
from .decision import decision as dec
from .memory import db, founder_score, ingest
from .screening import axes as axes_mod
from .screening import thesis as thesis_mod

app = FastAPI(title="VC Brain")
_DIST = config.ROOT / "frontend" / "dist"

from .api import evidence as _evidence_api  # noqa: E402
from .api import methodology as _methodology_api  # noqa: E402
from .api import network as _network_api  # noqa: E402
from .api import quality as _quality_api  # noqa: E402
app.include_router(_evidence_api.router)
app.include_router(_methodology_api.router)
app.include_router(_network_api.router)
app.include_router(_quality_api.router)


@app.on_event("startup")
def _seed_on_boot():
    """Deployed cold start must never be empty; no-op when founders exist."""
    from . import seed
    try:
        if seed.ensure_seeded():
            print("[seed] loaded snapshot into empty database")
    except Exception as e:  # a bad snapshot must not take the API down
        print(f"[seed] skipped: {type(e).__name__}: {e}")


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


# --- live run progress (apply -> memo) -------------------------------------
_RUN_STAGES = ("ingest", "screen", "news", "market", "extract", "adjudicate",
               "debate", "synthesize", "done")
_PIPELINE_STAGES = ("news", "market", "extract", "adjudicate", "debate", "synthesize")


def _set_stage(fid: str, stage: str, status: str, detail: str = "") -> None:
    conn = _conn()  # short-lived conn: safe from any thread
    conn.execute("DELETE FROM run_status WHERE founder_id=? AND stage=?", (fid, stage))
    conn.execute("INSERT INTO run_status (founder_id, stage, status, detail, updated_at) "
                 "VALUES (?,?,?,?,?)",
                 (fid, stage, status, detail, datetime.now(timezone.utc).isoformat()))
    conn.commit()


def _clear_stage(fid: str, stage: str) -> None:
    conn = _conn()
    conn.execute("DELETE FROM run_status WHERE founder_id=? AND stage=?", (fid, stage))
    conn.commit()


# The diligence pipeline times its stages via instrument.stage; wrap it (in this
# process only) so each stage also lands in run_status — the pipeline itself stays
# untouched, and progress is keyed by founder_id so concurrent runs don't collide.
_orig_stage = instrument.stage


@contextmanager
def _tracked_stage(conn, founder_id: str, name: str):
    _set_stage(founder_id, name, "running")
    try:
        with _orig_stage(conn, founder_id, name):
            yield
    except Exception as e:
        _set_stage(founder_id, name, "error", f"{type(e).__name__}: {e}")
        raise
    _set_stage(founder_id, name, "ok")


instrument.stage = _tracked_stage


def _run_pipeline_bg(fid: str, thesis_file: str | None, *, market: bool = True) -> None:
    """Background thread: full diligence on a fresh conn; errors land in run_status,
    never swallowed. market=True adds live Tavily market research (inbound applies);
    a forced diligence on an already-sourced founder skips it — the founder/traction
    analysis and decision are the point, and it keeps the run fast and dependency-free."""
    try:
        from .diligence import pipeline
        conn = _conn()
        t = _thesis(thesis_file)
        # News enrichment is intentionally OFF — general news feeds the founder-integrity
        # worker noisy web bios that manufacture false contradictions on real people;
        # it needs source-quality guardrails before it's safe to auto-enable.
        res = pipeline.run_diligence(conn, fid, t, replay=False, news=False, market=market)
        _set_stage(fid, "done", "ok",
                   f"{res['claims']} claims ({res['contested']} contested) -> "
                   f"decision: {res['recommendation'].decision}")
    except Exception as e:
        _set_stage(fid, "done", "error", f"{type(e).__name__}: {e}")


@app.get("/api/runs/{founder_id}")
def get_run(founder_id: str):
    """Ordered per-stage progress of a live apply->memo run, for a watchable UI."""
    conn = _conn()
    rows = conn.execute(
        "SELECT stage, status, detail, updated_at FROM run_status WHERE founder_id=?",
        (founder_id,)).fetchall()
    by = {r["stage"]: r for r in rows}
    lat = dict(instrument.latency_strip(conn, founder_id)["stages"])
    stages = [{"stage": s, "status": by[s]["status"], "detail": by[s]["detail"] or "",
               "updated_at": by[s]["updated_at"],
               "seconds": lat.get(s) if by[s]["status"] == "ok" else None}
              for s in _RUN_STAGES if s in by]
    has_memo = conn.execute("SELECT 1 FROM memos WHERE founder_id=? LIMIT 1",
                            (founder_id,)).fetchone() is not None
    done = by.get("done")
    state = (done["status"] if done and done["status"] in ("ok", "error")
             else "running" if rows else "none")
    return {"founder_id": founder_id, "stages": stages, "has_memo": has_memo,
            "state": state}


@app.post("/api/scan")
def scan(request: Request, source: str, topic: str | None = None,
         thesis: str | None = None):
    ratelimit.check("scan", request)
    """Live scan of ONE source (rate-limitable) with the real adapter — no replay.
    Per-source failures come back in counts as 'error: ...', never a 500."""
    from .sources import scanner
    valid = [n for n, _ in scanner.ADAPTERS]
    if source not in valid:
        raise HTTPException(422, f"source must be one of: {', '.join(valid)}")
    conn = _conn()
    t = _thesis(thesis)
    topics = scanner.topics_for(t, topic)
    res = scanner.run_scan(conn, topics, replay=False, limit_per=5, sources=[source])
    founders = []
    for fid, n in scanner.newly_resolved_founders(conn, res["new_signal_ids"]):
        row = conn.execute("SELECT name FROM founders WHERE id=?", (fid,)).fetchone()
        founders.append({"id": fid, "name": row["name"] if row else fid,
                         "new_signals": n})
    # res["dropped"] is a list[(signal_id, reason)]; the client shows a count and
    # the reasons, so expose both instead of stringifying the raw list.
    dropped = res["dropped"]
    return {"source": source, "topics": topics, "counts": res["counts"],
            "resolved": res["resolved"], "dropped": len(dropped),
            "dropped_detail": [{"signal_id": sid, "reason": reason} for sid, reason in dropped],
            "new_signals": len(res["new_signal_ids"]), "new_founders": founders}


class _FounderSummary(BaseModel):
    headline: str   # one line: the company/product and what it does
    summary: str    # 2-3 sentences on their startup work, grounded in the signals


# Embedded minimal default (promptlib scaffolding); mingjia owns the tuned override
# at prompts/founder_summary.md.
_SUMMARY_DEFAULT = (
    "You are a venture analyst. From a founder's raw public signals (GitHub, Hacker "
    "News, arXiv, Product Hunt, YC, or an inbound deck), describe WHAT they are building "
    "in plain, concrete language grounded ONLY in the signals provided.\n"
    "Return `headline`: one line naming the product/company and what it does. Return "
    "`summary`: 2-3 sentences on their startup work — the problem, the product, and any "
    "traction or technical angle visible in the signals.\n"
    "Do not invent facts, funding, customers, or metrics that are not present in the "
    "signals. If the signals are too thin to tell, say that plainly rather than guessing."
)


@app.get("/api/founders/{founder_id}/summary")
def founder_summary(founder_id: str, request: Request, thesis: str | None = None):
    """Plain-language LLM summary of what a founder is building, grounded in their raw
    signals — the concrete answer behind the abstract 'N topics · M sig'. Returns the
    underlying signals too, so the summary stays checkable against its sources. Falls
    back to signals-only (summary=null) when no LLM key/cache is available."""
    from . import llm
    from .promptlib import load_prompt
    ratelimit.check("summary", request)
    conn = _conn()
    row = conn.execute("SELECT name FROM founders WHERE id=?", (founder_id,)).fetchone()
    if not row:
        raise HTTPException(404, "no such founder")
    sigs = conn.execute(
        "SELECT s.source, s.source_url, s.content, s.observed_at FROM signals s "
        "LEFT JOIN resolutions r ON r.signal_id = s.id "
        "WHERE r.founder_id = ? OR s.founder_id = ? ORDER BY s.observed_at DESC",
        (founder_id, founder_id)).fetchall()
    signals = [{"source": s["source"], "source_url": s["source_url"],
                "excerpt": (s["content"] or "").strip()[:400],
                "observed_at": s["observed_at"]} for s in sigs]

    summary = None
    if signals:
        evidence = "\n\n".join(
            f"[{s['source']}] {s['excerpt']}"
            + (f"\n{s['source_url']}" if s["source_url"] else "")
            for s in signals)
        system = load_prompt("founder_summary", _SUMMARY_DEFAULT)
        user = (f"Founder: {row['name']}\n\n--- Signals ---\n{evidence}\n\n"
                "Describe what they are building.")
        try:
            out = llm.call("screen", system, user, _FounderSummary, replay=False,
                           max_tokens=400)
            summary = {"headline": out.headline, "summary": out.summary}
        except Exception:
            # no key + cache miss (offline demo) — the raw signals still answer the "what".
            summary = None
    return {"founder_id": founder_id, "name": row["name"],
            "signal_count": len(signals), "summary": summary, "signals": signals}


@app.get("/api/theses")
def theses():
    out = []
    for p in sorted((config.ROOT / "config").glob("thesis_*.yaml")):
        t = thesis_mod.load_thesis(p)
        # full config, not just the name: the Thesis page loads one back into the
        # editor, so the client needs the fields it is about to edit.
        out.append({"file": f"config/{p.name}", **asdict(t)})
    return out


@app.get("/api/founders")
def founders(thesis: str | None = None):
    conn = _conn()
    t = _thesis(thesis)
    ids = [r["fid"] for r in conn.execute(
        "SELECT DISTINCT founder_id fid FROM axis_scores").fetchall()]
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    # Batch every per-founder lookup into set-based queries: on remote Postgres each
    # round-trip is ~30-60ms, so the old per-founder loop was seconds of pure latency.
    names = {r["id"]: r["name"] for r in conn.execute(
        f"SELECT id, name, founder_score FROM founders WHERE id IN ({marks})", ids)}
    histories = {r["id"]: json.loads(r["founder_score"] or "{}").get("history", [])
                 for r in conn.execute(
                     f"SELECT id, founder_score FROM founders WHERE id IN ({marks})", ids)}
    memos = {r["fid"] for r in conn.execute(
        f"SELECT DISTINCT founder_id fid FROM memos WHERE founder_id IN ({marks})", ids)}
    lat_tot = {r["fid"]: r["tot"] for r in conn.execute(
        f"SELECT founder_id fid, SUM(seconds) tot FROM latency "
        f"WHERE founder_id IN ({marks}) GROUP BY founder_id", ids)}
    src = {}
    for r in conn.execute(
            f"SELECT COALESCE(r.founder_id, s.founder_id) fid, s.source FROM signals s "
            f"LEFT JOIN resolutions r ON r.signal_id=s.id "
            f"WHERE r.founder_id IN ({marks}) OR s.founder_id IN ({marks})", ids + ids):
        if r["fid"] and (r["fid"] not in src or r["source"] < src[r["fid"]]):
            src[r["fid"]] = r["source"]  # alphabetically-first source, as before
    axes_by = dec.per_axis_batch(conn, ids, t.name)  # thesis lens actually applied
    scores = founder_score.compute_batch(conn, ids)
    out = []
    for fid in ids:
        # Signal / Coverage split (spec §3): Signal = persistent Founder Score
        # (evidence-derived, deterministic); Coverage = fraction of the record's
        # informational areas with >=1 claim. NOT derived from the 3 axes.
        cur, hist = scores[fid], histories.get(fid) or []
        out.append({"id": fid, "name": names.get(fid, fid),
                    "source": src.get(fid, "unknown"), "axes": axes_by[fid],
                    "signal": cur["score"], "coverage": cur["coverage"],
                    "score_history_points": len(hist), "score_history": hist,
                    "has_memo": fid in memos, "latency_total": lat_tot.get(fid) or 0})
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
    st = founder_score.stored(conn, founder_id)
    brief["score_history"] = st["history"] if st else []
    cur = founder_score.compute(conn, founder_id)
    brief["signal"] = cur["score"]
    brief["coverage"] = cur["coverage"]
    return brief


@app.get("/api/memo/{founder_id}.pdf")
def memo_pdf(founder_id: str, thesis: str | None = None):
    """Shareable investment-memo PDF — the artifact a VC actually emails around."""
    from fastapi.responses import Response

    from . import memo_pdf as pdf
    conn = _conn()
    row = conn.execute(
        "SELECT thesis, decision, memo_md, created_at FROM memos WHERE founder_id=? "
        "ORDER BY created_at DESC LIMIT 1", (founder_id,)).fetchone()
    if not row:
        raise HTTPException(404, "no memo for this founder — run diligence first")
    name = conn.execute("SELECT name FROM founders WHERE id=?", (founder_id,)).fetchone()
    company = (name["name"] if name else founder_id).split("/")[-1].strip()
    cur = founder_score.compute(conn, founder_id)
    data = pdf.render(company, row["thesis"], row["decision"], cur["score"],
                      cur["coverage"], row["memo_md"], (row["created_at"] or "")[:10])
    slug = company.lower().replace(" ", "-") or founder_id
    return Response(content=data, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{slug}-memo.pdf"'})


@app.get("/api/sourcing")
def sourcing(thesis: str | None = None):
    """Ranked outbound feed: every resolved founder (screened or not), ranked by
    thesis-topic match + signal count. Includes the drop-log tally — 'nothing
    discarded' rendered as a feature."""
    conn = _conn()
    t = _thesis(thesis)
    # Founder name/keys folded into the aggregate (1:1 with founder_id, so listing them
    # in GROUP BY is engine-portable) — removes one per-founder lookup from the loop.
    rows = conn.execute(
        "SELECT r.founder_id fid, f.name name, f.entity_keys entity_keys, "
        "COUNT(*) n, GROUP_CONCAT(DISTINCT s.source) sources, "
        "MAX(COALESCE(s.observed_at, s.ingested_at)) latest, "
        "GROUP_CONCAT(s.content, '\n') blob "
        "FROM resolutions r JOIN signals s ON s.id = r.signal_id "
        "JOIN founders f ON f.id = r.founder_id "
        "GROUP BY r.founder_id, f.name, f.entity_keys").fetchall()
    screened = {r["fid"] for r in conn.execute(
        "SELECT DISTINCT founder_id fid FROM axis_scores").fetchall()}
    outreach = {r["fid"] for r in conn.execute(
        "SELECT DISTINCT founder_id fid FROM outreach").fetchall()}
    scores = founder_score.compute_batch(conn, [r["fid"] for r in rows])
    out = []
    for r in rows:
        blob = (r["blob"] or "").lower()
        topic_match = sum(1 for tp in t.topics if tp.lower() in blob)
        cur = scores[r["fid"]]
        out.append({"id": r["fid"], "name": r["name"] or r["fid"],
                    "signal": cur["score"], "coverage": cur["coverage"],
                    "dimensions": cur["dimensions"],
                    "entity_keys": json.loads(r["entity_keys"]) if r["entity_keys"] else {},
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
def nl_query(q: str, request: Request):
    ratelimit.check("query", request)
    """Multi-attribute NL query (MVP 3): one cached model call parses; Memory filters.
    Non-evaluable criteria are flagged and ignored, never guessed."""
    from . import query as query_mod
    conn = _conn()
    try:
        return query_mod.run(conn, q, replay=config.replay_enabled(None))
    except Exception as e:  # parse failure / replay miss / no key — explain, don't 422
        return {"query": q, "criteria": [], "ignored_criteria": [], "results": [],
                "error": f"The query could not be parsed ({type(e).__name__}: {e}). "
                         "Nothing was guessed — try rephrasing, or check the LLM key."}


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
        (*sig_ids, row["evidence_url"])).fetchall()
    adj = conn.execute(
        "SELECT * FROM adjudications WHERE founder_id=? AND claim_id=? "
        "ORDER BY decided_at DESC LIMIT 1", (founder_id, claim_id)).fetchone()
    from .diligence.ledger import rubric_trust
    return {
        "claim": {"id": row["claim_id"], "axis": row["axis"], "text": row["text"],
                  "stance": row["stance"], "evidence": row["evidence"],
                  "evidence_url": row["evidence_url"],
                  "evidence_title": row["evidence_title"],
                  "evidence_excerpt": row["evidence_excerpt"],
                  "retrieved_at": row["retrieved_at"],
                  "source_type": row["source_type"],
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
def apply(body: Application, request: Request):
    ratelimit.check("apply", request)
    """Inbound intake (MVP 4): deck + company name is the minimum bar. The deck
    lands as a self-reported signal in the same funnel as outbound. Screening runs
    synchronously; if it passes the first-pass kill screen, the FULL diligence
    pipeline runs in a background thread — poll GET /api/runs/{founder_id}."""
    if not body.company.strip() or not body.deck_text.strip():
        raise HTTPException(422, "company and deck_text are required — nothing else is")
    return _intake(body.company, body.deck_text)


@app.post("/api/apply/pdf")
def apply_pdf(request: Request, company: str = Form(...), file: UploadFile = File(...)):
    """Same intake, PDF instead of pasted text. The deck is parsed to plain text
    here and then follows the identical path — extraction is the only difference,
    so a PDF applicant is not a second-class citizen in the funnel. The filename
    rides in source_url so provenance stays visible on the claim trail."""
    # Parse BEFORE spending rate-limit budget: the limiter protects LLM spend, and a
    # rejected upload costs none. Otherwise three bad files lock a judge out for an hour.
    if not company.strip():
        raise HTTPException(422, "company is required")
    try:
        deck_text = deck_pdf.extract(file.file.read(), file.filename or "deck.pdf")
    except deck_pdf.DeckPdfError as e:
        raise HTTPException(422, str(e)) from e
    ratelimit.check("apply", request)
    return _intake(company, deck_text, origin=file.filename or "deck.pdf")


def _intake(company: str, deck_text: str, origin: str | None = None):
    """Shared inbound funnel: store the deck as a self-reported signal, run the
    first-pass screen synchronously, then hand off to full diligence if it lives."""
    import re as _re

    from .memory.models import Founder, Signal
    conn = _conn()
    fid = "founder-" + _re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")
    ingest.upsert_founder(conn, Founder(id=fid, name=company))
    # Origin varies the source_url so re-uploading the same PDF dedups against
    # itself, while a pasted summary stays a distinct signal from the deck file.
    url = f"application://{fid}" + (f"/{origin}" if origin else "")
    sid, inserted = ingest.ingest_signal(conn, Signal(
        source="deck", source_url=url, content=deck_text,
        observed_at=config.DEMO_TODAY, founder_id=fid))
    _set_stage(fid, "ingest", "ok",
               f"signal {sid}" + (" (duplicate — deck already on file)" if not inserted else ""))
    for st in ("screen",) + _PIPELINE_STAGES + ("done",):
        _set_stage(fid, st, "queued")

    from . import llm as llm_mod
    screened, screen_error, killed = False, None, False
    if llm_mod.provider() is None and not config.replay_enabled(None):
        screen_error = "no LLM key configured — application stored, screening skipped"
        _set_stage(fid, "screen", "error", screen_error)
        for st in _PIPELINE_STAGES:
            _clear_stage(fid, st)
        _set_stage(fid, "done", "error", screen_error)
    else:
        _set_stage(fid, "screen", "running")
        try:
            from .screening import axes as axes_mod
            res = axes_mod.screen(conn, fid, _thesis(None),
                                  replay=config.replay_enabled(None))
            screened = True
            if res.get("killed"):
                killed = True
                reason = res.get("kill_reason", "")
                _set_stage(fid, "screen", "ok", f"killed at first pass: {reason}")
                for st in _PIPELINE_STAGES:  # never ran — drop, don't fake
                    _clear_stage(fid, st)
                _set_stage(fid, "done", "ok",
                           f"no memo — killed at first-pass screen: {reason}")
            else:
                _set_stage(fid, "screen", "ok", "3 axes scored independently")
        except Exception as e:  # founder is stored either way; the failure is surfaced
            screen_error = f"{type(e).__name__}: {e}"
            _set_stage(fid, "screen", "error", screen_error)
            for st in _PIPELINE_STAGES:
                _clear_stage(fid, st)
            _set_stage(fid, "done", "error", screen_error)

    run_started = screened and not killed
    if run_started:
        threading.Thread(target=_run_pipeline_bg, args=(fid, None), daemon=True).start()
    return {"founder_id": fid, "signal_id": sid, "duplicate": not inserted,
            "screened": screened, "screen_error": screen_error, "killed": killed,
            "run_started": run_started}


@app.post("/api/diligence/{founder_id}")
def force_diligence(founder_id: str, request: Request, thesis: str | None = None):
    ratelimit.check("diligence", request)
    """Force an already-screened founder into FULL diligence, overriding the
    first-pass kill screen. This is the manual analyst override: the screen gate is
    a triage heuristic, not a verdict, so a partner can always pull a specific
    founder through. Runs the same pipeline as an inbound apply (background thread;
    poll GET /api/runs/{founder_id})."""
    conn = _conn()
    if not conn.execute("SELECT 1 FROM founders WHERE id=?", (founder_id,)).fetchone():
        raise HTTPException(404, "no such founder — source or apply them first")

    # Don't stack a second run on top of one already in flight — but a run whose
    # thread died (process restart, crash) leaves non-terminal rows forever; treat
    # anything that hasn't advanced in 15 min as abandoned so it can be re-forced.
    rows = conn.execute(
        "SELECT stage, status, updated_at FROM run_status WHERE founder_id=?",
        (founder_id,)).fetchall()
    done = next((r for r in rows if r["stage"] == "done"), None)
    terminal = done is not None and done["status"] in ("ok", "error")
    fresh = False
    if rows:
        last = max(r["updated_at"] for r in rows)
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds()
            fresh = age < 900
        except ValueError:
            fresh = True
    running = bool(rows) and not terminal and fresh
    has_memo = conn.execute("SELECT 1 FROM memos WHERE founder_id=? LIMIT 1",
                            (founder_id,)).fetchone() is not None
    if running:
        return {"founder_id": founder_id, "run_started": False,
                "already_running": True, "has_memo": has_memo}

    from . import llm as llm_mod
    if llm_mod.provider() is None and not config.replay_enabled(None):
        raise HTTPException(422, "no LLM key configured — diligence needs a model")

    # Rebuild the run strip: screen is marked forced (kill overridden), not re-run.
    # Only the stages that will actually run are queued (no news/market for a force).
    _set_stage(founder_id, "ingest", "ok", "already sourced — using signals on file")
    _set_stage(founder_id, "screen", "ok", "forced into diligence — kill screen overridden")
    for st in ("extract", "adjudicate", "debate", "synthesize", "done"):
        _set_stage(founder_id, st, "queued")
    threading.Thread(target=_run_pipeline_bg, args=(founder_id, thesis),
                     kwargs={"market": False}, daemon=True).start()
    return {"founder_id": founder_id, "run_started": True,
            "already_running": False, "has_memo": has_memo, "forced": True}


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
def activate_founder(founder_id: str, request: Request, thesis: str | None = None):
    ratelimit.check("activate", request)
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
    replaces: str | None = None  # file being edited; removed when a rename moves it


def _thesis_path(file: str) -> Path:
    """Resolve a client-supplied thesis file. The name arrives from the browser, so
    it must land inside config/ and look like a thesis config — nothing else."""
    cfg_dir = (config.ROOT / "config").resolve()
    p = (config.ROOT / file).resolve()
    if p.parent != cfg_dir or not p.name.startswith("thesis_") or p.suffix != ".yaml":
        raise HTTPException(400, "not a thesis config path")
    if not p.exists():
        raise HTTPException(404, "thesis not found")
    return p


@app.post("/api/thesis")
def save_thesis(body: ThesisConfig):
    """Thesis Engine is configurable (brief FAQ 15): persist an investor-edited
    thesis as a YAML config next to the built-ins. Pass `replaces` to edit an
    existing one — renaming it moves the file rather than leaving an orphan."""
    import re as _re

    import yaml
    slug = _re.sub(r"[^a-z0-9]+", "_", body.name.lower()).strip("_") or "custom"
    path = config.ROOT / "config" / f"thesis_{slug}.yaml"
    old = _thesis_path(body.replaces) if body.replaces else None
    path.write_text(yaml.safe_dump(body.model_dump(exclude={"replaces"}),
                                   sort_keys=False))
    if old and old != path:
        old.unlink()
    return {"file": f"config/{path.name}", "name": body.name}


@app.delete("/api/thesis")
def delete_thesis(file: str):
    """Delete a thesis config. The engine always needs one lens, so the last one
    can't go — that's a 409, not a silent no-op."""
    path = _thesis_path(file)
    remaining = sorted(p for p in (config.ROOT / "config").glob("thesis_*.yaml")
                       if p != path)
    if not remaining:
        raise HTTPException(409, "cannot delete the last thesis — the engine needs a lens")
    path.unlink()
    return {"deleted": f"config/{path.name}", "next": f"config/{remaining[0].name}"}


class AskBody(BaseModel):
    question: str


@app.post("/api/ask/{founder_id}")
def ask_memo(founder_id: str, body: AskBody, request: Request):
    """Grounded Q&A: answers ONLY from the claim ledger, cites claim ids, refuses
    when the ledger doesn't support an answer. A mechanical (no-LLM) validator
    strips any cited id that doesn't exist — same guarantee as the memo validator."""
    ratelimit.check("ask", request)
    from . import llm as llm_mod
    from . import promptlib
    from .diligence.schemas import AskAnswer
    if not body.question.strip():
        raise HTTPException(422, "question is required")
    conn = _conn()
    claims = ingest.get_claims(conn, founder_id)
    if not claims:
        raise HTTPException(404, "no claim ledger for this founder — run diligence first")
    if llm_mod.provider() is None and not config.replay_enabled(None):
        raise HTTPException(409, "no LLM key and not in replay — cannot answer")
    system = promptlib.load_prompt("ask_memo", default=(
        "Answer investor questions using ONLY the provided claim ledger. Cite claim "
        "ids in brackets for every factual sentence. If the ledger cannot support an "
        "answer, set refused=true and say what is missing. Never use outside "
        "knowledge or estimate missing values."))
    ledger_txt = "\n".join(
        f"[{c.id}] ({c.axis}, {c.corroboration}, trust={c.trust}) {c.stance}: {c.text}"
        for c in claims)
    out = llm_mod.call("worker", system,
                       f"CLAIM LEDGER:\n{ledger_txt}\n\nQUESTION: {body.question}",
                       AskAnswer, replay=config.replay_enabled(None))
    valid = {c.id for c in claims}
    cited = [i for i in out.cited_claim_ids if i in valid]
    invalid = [i for i in out.cited_claim_ids if i not in valid]
    refused = out.refused or (not cited and not out.refused and bool(invalid))
    return {"question": body.question, "answer": out.answer,
            "cited_claim_ids": cited, "invalid_citations": invalid,
            "refused": refused,
            "validated": not invalid}


@app.get("/api/killed")
def killed():
    conn = _conn()
    # One row per founder, carrying their LATEST kill reason. A bare `GROUP BY
    # founder_id` selecting an ungrouped `reason` is legal in SQLite but Postgres
    # rejects it, so this endpoint 500'd in deploy while the tests (SQLite) passed.
    rows = conn.execute(
        "SELECT DISTINCT k.founder_id, "
        "(SELECT reason FROM kill_log k2 WHERE k2.founder_id = k.founder_id "
        "ORDER BY logged_at DESC LIMIT 1) reason FROM kill_log k").fetchall()
    return [{"id": r["founder_id"], "reason": r["reason"]} for r in rows]


# --- static SPA (built bundle) ---
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/")
    def index():
        # index.html references content-hashed asset filenames, so it must NOT be
        # cached — otherwise a returning browser loads a stale index that points at
        # an old bundle and never sees a new deploy. The hashed assets under /assets
        # can cache forever (their name changes when content changes).
        return FileResponse(_DIST / "index.html",
                            headers={"Cache-Control": "no-cache, must-revalidate"})
