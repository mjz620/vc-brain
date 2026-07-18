"""Multi-attribute NL query (brief MVP 3): one model call parses the compound query
into structured criteria, then a mechanical filter + rank runs over Memory.

Honesty rule: a criterion Memory cannot evaluate (e.g. "no prior VC backing" when no
funding-history source is ingested) is returned as not_evaluable and IGNORED in the
filter — flagged to the user, never silently guessed.
"""
from typing import Literal

from pydantic import BaseModel

from . import llm
from .memory import founder_score
from .promptlib import load_prompt

_DEFAULT = (
    "Parse an investor's compound natural-language founder query into structured "
    "criteria. Memory can evaluate ONLY these criterion kinds:\n"
    "- keyword: a sector/technology/traction term to match against signal text "
    "(e.g. 'ai infra' -> keywords like 'llm', 'infra', 'agents'; 'enterprise traction' "
    "-> 'enterprise', 'customers')\n"
    "- source: restrict to a sourcing channel: github, hn, arxiv, producthunt, yc "
    "('top-tier accelerator' -> source yc; 'published research' -> arxiv; "
    "'technical founder' -> source github)\n"
    "- score: a minimum Founder Score 0-10, value like '7' ('strong signal' -> 7)\n"
    "Anything Memory cannot evaluate (geography, prior VC backing, headcount, "
    "demographics) MUST be kind=not_evaluable with the reason in value — do NOT force "
    "it into a keyword. Split the query exhaustively; every fragment lands in exactly "
    "one criterion.")


class Criterion(BaseModel):
    text: str  # the query fragment, verbatim
    kind: Literal["keyword", "source", "score", "not_evaluable"]
    value: str


class ParsedQuery(BaseModel):
    criteria: list[Criterion]


def parse(q: str, *, replay: bool) -> ParsedQuery:
    return llm.call("worker", load_prompt("nl_query", _DEFAULT),
                    f"Query: {q}", ParsedQuery, replay=replay, max_tokens=500)


def run(conn, q: str, *, replay: bool, limit: int = 15) -> dict:
    parsed = parse(q, replay=replay)
    keywords = [c.value.lower() for c in parsed.criteria if c.kind == "keyword"]
    sources = {c.value.lower() for c in parsed.criteria if c.kind == "source"}
    min_scores = [float(c.value) for c in parsed.criteria
                  if c.kind == "score" and c.value.replace(".", "").isdigit()]
    ignored = [c for c in parsed.criteria if c.kind == "not_evaluable"]

    rows = conn.execute(
        "SELECT r.founder_id fid, GROUP_CONCAT(DISTINCT s.source) sources, "
        "GROUP_CONCAT(s.content, '\n') blob "
        "FROM resolutions r JOIN signals s ON s.id = r.signal_id "
        "GROUP BY r.founder_id").fetchall()
    results = []
    for r in rows:
        blob = (r["blob"] or "").lower()
        founder_sources = set((r["sources"] or "").lower().split(","))
        kw_hits = [k for k in keywords if k in blob]
        if sources and not (sources & founder_sources):
            continue
        if keywords and not kw_hits:
            continue
        cur = founder_score.compute(conn, r["fid"])
        if min_scores and (cur["score"] is None or cur["score"] < max(min_scores)):
            continue
        f = conn.execute("SELECT name FROM founders WHERE id=?", (r["fid"],)).fetchone()
        results.append({"id": r["fid"], "name": f["name"] if f else r["fid"],
                        "signal": cur["score"], "coverage": cur["coverage"],
                        "sources": sorted(founder_sources),
                        "matched_keywords": kw_hits})
    results.sort(key=lambda x: (len(x["matched_keywords"]), x["signal"] or 0),
                 reverse=True)
    return {
        "query": q,
        "criteria": [c.model_dump() for c in parsed.criteria],
        "ignored_criteria": [
            {"text": c.text, "reason": c.value} for c in ignored],
        "results": results[:limit],
    }
