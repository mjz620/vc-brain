"""Persistent Founder Score (brief Memory pillar, FAQ 6): lives in Memory, persists
across applications, never resets — one INPUT into the Founder axis, not a substitute.

Deterministic: computed mechanically from signals + claims in Memory, no LLM call.
Every dimension is either evidenced or None ("unassessed") — a cold-start founder gets
a low-COVERAGE flag, not a fabricated low score (spec §3). The composite ("Signal") is
a weighted mean over the ASSESSED dimensions only. This is not the 3-axis screen and
averages nothing from it.
"""
import json
import math
import re
from types import SimpleNamespace

from . import ingest
from .models import ScoreEntry

_STARS = re.compile(r"stars=(\d+)")
_POINTS = re.compile(r"points=(\d+)")
_VELOCITY = re.compile(r"velocity: commits_6w=(\d+) active_days=(\d+)")
_OUTBOUND = ("github", "hn", "arxiv", "producthunt", "yc")

# dimension -> weight in the composite (renormalized over assessed dimensions)
WEIGHTS = {"execution_velocity": 0.35, "community_pull": 0.25, "domain_breadth": 0.1,
           "integrity": 0.15, "verified_depth": 0.15}

# Record-coverage checklist: the memo's informational areas. coverage = evidenced/13.
# A contradicted claim still covers its area (evidence was gathered; it just failed).
COVERAGE_AREAS = [
    ("founder background", {"founder"}, []),
    ("market sizing", {"market"}, []),
    ("competition", set(), ["compet", "incumbent"]),
    ("product", {"idea"}, ["product", "integration", "live"]),
    ("traction", {"traction"}, []),
    ("revenue", set(), ["arr", "revenue"]),
    ("customers", set(), ["customer", "design partner"]),
    ("churn", set(), ["churn"]),
    ("cac", set(), ["cac"]),
    ("sales cycle", set(), ["sales cycle"]),
    ("usage metrics", set(), ["dau", "usage"]),
    ("financials/round", set(), ["round", "runway", "raising"]),
    ("cap table", set(), ["cap table", "ownership", "dilution"]),
]


def _signals(conn, founder_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT s.source, s.content FROM signals s "
        "LEFT JOIN resolutions r ON r.signal_id = s.id "
        "WHERE r.founder_id = ? OR s.founder_id = ?",
        (founder_id, founder_id)).fetchall()]


def dimensions(signals: list[dict], claims) -> dict[str, float | None]:
    blob = "\n".join(s["content"] for s in signals)

    vel = None
    m = _VELOCITY.search(blob)
    if m:
        commits, days = int(m.group(1)), int(m.group(2))
        # 60 commits + 30 active days over the 6-week window saturate the dimension.
        vel = round(min(6.0, commits * 6 / 60) + min(4.0, days * 4 / 30), 1)

    engagement = [int(x) for x in _STARS.findall(blob) + _POINTS.findall(blob)]
    pull = (round(min(10.0, 3 * math.log10(1 + max(engagement))), 1)
            if engagement else None)

    srcs = {s["source"] for s in signals if s["source"] in _OUTBOUND}
    breadth = round(min(10.0, 2 + 2 * len(srcs)), 1) if srcs else None

    integrity = depth = None
    if claims:
        contradicted = sum(1 for c in claims if c.corroboration == "contradicted")
        integrity = round(10 * (1 - contradicted / len(claims)), 1)
        # verified_depth: how much of the record is externally corroborated — keeps an
        # inbound founder's composite from collapsing to the integrity dimension alone.
        corr = sum(1 for c in claims if c.corroboration == "corroborated")
        depth = round(10 * corr / len(claims), 1)

    return {"execution_velocity": vel, "community_pull": pull,
            "domain_breadth": breadth, "integrity": integrity,
            "verified_depth": depth}


def coverage_of(claims) -> float:
    texts = [(c.axis, c.text.lower()) for c in claims]
    hit = 0
    for _, axes, kws in COVERAGE_AREAS:
        if any(ax in axes or any(k in t for k in kws) for ax, t in texts):
            hit += 1
    return round(hit / len(COVERAGE_AREAS), 2)


def composite(dims: dict[str, float | None]) -> float | None:
    assessed = {k: v for k, v in dims.items() if v is not None}
    if not assessed:
        return None
    total_w = sum(WEIGHTS[k] for k in assessed)
    return round(sum(v * WEIGHTS[k] for k, v in assessed.items()) / total_w, 1)


def compute(conn, founder_id: str) -> dict:
    """Pure computation: current dimensions, coverage, composite. No writes."""
    claims = ingest.get_claims(conn, founder_id)
    dims = dimensions(_signals(conn, founder_id), claims)
    return {"dimensions": dims, "coverage": coverage_of(claims),
            "score": composite(dims)}


def compute_batch(conn, founder_ids: list[str]) -> dict[str, dict]:
    """compute() for many founders in a fixed 2 queries instead of N+1.

    Identical arithmetic to compute() — it feeds the SAME pure dimensions()/
    coverage_of()/composite() functions, just with batch-loaded evidence. This is a
    read-path latency fix (remote Postgres makes every round-trip expensive), not a
    scoring change.
    """
    if not founder_ids:
        return {}
    ids = list(dict.fromkeys(founder_ids))
    marks = ",".join("?" * len(ids))

    # All claims for these founders, one query. Only the fields the pure scorers read.
    claims_by: dict[str, list] = {fid: [] for fid in ids}
    for r in conn.execute(
            f"SELECT founder_id, axis, text, corroboration FROM claims "
            f"WHERE founder_id IN ({marks})", ids).fetchall():
        claims_by[r["founder_id"]].append(SimpleNamespace(
            axis=r["axis"], text=r["text"], corroboration=r["corroboration"]))

    # All signals for these founders, one query. A signal counts for a founder if it
    # resolves to them OR is directly owned by them (matches _signals()'s OR clause).
    sigs_by: dict[str, list] = {fid: [] for fid in ids}
    idset = set(ids)
    for r in conn.execute(
            f"SELECT s.source, s.content, r.founder_id rfid, s.founder_id sfid "
            f"FROM signals s LEFT JOIN resolutions r ON r.signal_id = s.id "
            f"WHERE r.founder_id IN ({marks}) OR s.founder_id IN ({marks})",
            ids + ids).fetchall():
        sig = {"source": r["source"], "content": r["content"]}
        for fid in {r["rfid"], r["sfid"]} & idset:
            sigs_by[fid].append(sig)

    out = {}
    for fid in ids:
        claims = claims_by[fid]
        dims = dimensions(sigs_by[fid], claims)
        out[fid] = {"dimensions": dims, "coverage": coverage_of(claims),
                    "score": composite(dims)}
    return out


def recompute(conn, founder_id: str, trigger: str, *, now: str) -> dict:
    """Compute and APPEND to the founder's score history (never overwrite, never
    reset — re-running appends, so the trend over time falls out for free)."""
    cur = compute(conn, founder_id)
    if cur["score"] is not None:
        ingest.append_score(
            conn, founder_id,
            ScoreEntry(timestamp=now, score=cur["score"], trigger=trigger),
            dimensions={k: v for k, v in cur["dimensions"].items() if v is not None},
            coverage=cur["coverage"])
    return cur


def stored(conn, founder_id: str) -> dict | None:
    row = conn.execute("SELECT founder_score FROM founders WHERE id=?",
                       (founder_id,)).fetchone()
    if not row or not row["founder_score"]:
        return None
    fs = json.loads(row["founder_score"])
    return fs if fs.get("history") else None
