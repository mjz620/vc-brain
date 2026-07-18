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
from .memory import db, ingest
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
        # signal / coverage split (spec §3): max axis score + mean coverage
        scored = [a for a in axes if "score" in a]
        signal = max((a["score"] for a in scored), default=0)
        coverage = (sum(a["coverage"] for a in scored) / len(scored)) if scored else 0
        out.append({"id": fid, "name": name["name"] if name else fid,
                    "source": _source_of(conn, fid), "axes": axes,
                    "signal": round(signal, 1), "coverage": round(coverage, 2),
                    "has_memo": has_memo, "latency_total": lat["total_seconds"]})
    # rank by signal desc (unblended axes stay separate in the payload)
    out.sort(key=lambda f: f["signal"], reverse=True)
    return out


@app.get("/api/founders/{founder_id}")
def founder(founder_id: str, thesis: str | None = None):
    conn = _conn()
    t = _thesis(thesis)
    brief = dec.build(conn, founder_id, t)
    claims = [c.model_dump() for c in ingest.get_claims(conn, founder_id)]
    brief["claims"] = claims  # for click-to-evidence
    return brief


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
