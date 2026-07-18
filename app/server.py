"""FastAPI backend: JSON endpoints over Memory + serves the built React bundle.

No LLM calls except the optional NL-query endpoint (cached). Read-only over vc_brain.db.
"""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
    ids = [r["fid"] for r in conn.execute(
        "SELECT DISTINCT founder_id fid FROM axis_scores").fetchall()]
    out = []
    for fid in ids:
        name = conn.execute("SELECT name FROM founders WHERE id=?", (fid,)).fetchone()
        axes = dec.per_axis(conn, fid)
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
