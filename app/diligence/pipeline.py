"""Diligence orchestrator: evidence -> workers -> ledger -> fact-layer adjudication ->
decision-layer debate -> synthesizer -> critic -> stored memo (spec §2.4)."""
import os
from datetime import datetime, timezone

from pydantic import BaseModel

from .. import cache, instrument, llm
from ..memory import founder_score, ingest
from ..promptlib import load_prompt
from ..memory.models import Signal
from ..screening import thesis as thesis_mod
from ..sources import tavily
from ..sources.http import domain_of
from . import adjudicate, critic, debate, ledger, loader, synthesizer, workers

# Demo fixture founders: news enrichment must NEVER run for these ids. Their worker
# evidence feeds the llm cache key — new signals would silently regenerate the three
# demo memos' claims (CLAUDE.md: demo determinism / fixture integrity).
FIXTURE_FOUNDER_IDS = {fid for fid, _ in loader.FIXTURES.values()}

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


def _news_queries(conn, founder_id: str) -> list[str]:
    """1-2 news queries from the founder's name/company (+ deck company line)."""
    row = conn.execute("SELECT name FROM founders WHERE id = ?", (founder_id,)).fetchone()
    if row is None:
        raise KeyError(f"unknown founder {founder_id}")
    parts = [p.strip() for p in row["name"].split("/") if p.strip()]
    queries = [" ".join(parts)]
    deck = conn.execute("SELECT content FROM signals WHERE founder_id = ? AND "
                        "source = 'deck' LIMIT 1", (founder_id,)).fetchone()
    if deck:
        first = next((l.strip() for l in deck["content"].splitlines() if l.strip()), "")
        if 0 < len(first) <= 60 and first not in queries:
            queries.append(f"{first} startup funding")
    elif len(parts) >= 2:
        queries.append(f"{parts[-1]} startup funding")
    return queries[:2]


def enrich_news(conn, founder_id: str, *, replay: bool) -> list[dict]:
    """Tavily news enrichment: search -> ingest results as tavily signals ->
    extract top URLs for fuller content. Returns what was found (title/url/date).

    SAFE FOR NOVEL FOUNDERS ONLY (new inbound applies). Hard-refused for the three
    demo fixture founders — added signals change worker evidence and therefore llm
    cache keys, which would silently regenerate the cached demo claims.
    Raises RuntimeError/ReplayMiss when no key is set and the cache misses.
    """
    if founder_id in FIXTURE_FOUNDER_IDS:
        raise ValueError(f"news enrichment refused for fixture founder {founder_id} "
                         "(demo determinism guardrail)")
    found: list[dict] = []
    ranked: list[tuple[float, str]] = []
    for q in _news_queries(conn, founder_id):
        resp = tavily.news_search(q, replay=replay)
        for r in resp.get("results", []):
            if not r.get("url"):
                continue
            ingest.ingest_signal(conn, Signal(
                source="tavily", source_url=r["url"],
                content=f"{r.get('title', '')} | {r.get('content', '')}",
                observed_at=r.get("published_date"), founder_id=founder_id))
            ranked.append((r.get("score", 0.0), r["url"]))
            found.append({"title": r.get("title"), "url": r["url"],
                          "published_date": r.get("published_date")})
    top = [u for _, u in sorted(ranked, reverse=True)[:3]]
    if top:
        ext = tavily.extract(top, replay=replay)
        for r in ext.get("results", []):
            if r.get("raw_content"):
                ingest.ingest_signal(conn, Signal(
                    source="tavily", source_url=r["url"],
                    content=r["raw_content"][:4000], founder_id=founder_id))
    return found


class _Category(BaseModel):
    category: str


_CATEGORY_DEFAULT = (
    "Name the product category this company sells into, as an industry analyst would "
    "label it for market sizing. Use the standard category name people publish TAM "
    "figures for (e.g. 'IT service management (ITSM) software', 'observability', "
    "'contract lifecycle management'), NOT the company name and NOT a broad sector "
    "like 'AI' or 'SaaS'. Reply with the category alone, no punctuation or preamble.")


def _category_of(conn, founder_id: str, company: str, *, replay: bool) -> str | None:
    """The category an analyst would size — derived from what the company actually
    sells, never from the fund thesis. This is the distinction that keeps sizing
    honest: 'ITSM software' is THIS company's market; 'AI infra' is the thesis's.

    Returns None if there is nothing to derive it from, in which case sizing is
    skipped and the market worker's 'not derivable' claim stands truthfully.
    """
    row = conn.execute(
        "SELECT content FROM signals WHERE founder_id = ? AND source = 'deck' LIMIT 1",
        (founder_id,)).fetchone()
    if row is None or not (row["content"] or "").strip():
        return None
    out = llm.call(
        "worker", load_prompt("market_category", _CATEGORY_DEFAULT),
        f"Company: {company}\n\n{row['content'][:2000]}", _Category,
        replay=replay, max_tokens=60)
    cat = " ".join((out.category or "").split()).strip(" .\"'")
    return cat or None


def _market_queries(conn, founder_id: str, *, replay: bool) -> list[str]:
    """Company-scoped queries (the niche market and the competitive set) PLUS
    category-scoped sizing queries.

    Still deliberately NOT the broad thesis sector — that is the category error the
    company-scoped queries were guarding against, and it stays guarded because the
    category is derived from the company's own deck, not from the thesis. And still
    never the company's own funding, which would leak into the founder-integrity
    check and manufacture false contradictions.

    The company-scoped sizing query alone returns nothing for an unknown two-person
    startup, which is why sizing previously came back 'not derivable' — the worker
    was right, it simply had no evidence to work from.
    """
    row = conn.execute("SELECT name FROM founders WHERE id = ?", (founder_id,)).fetchone()
    if row is None:
        raise KeyError(f"unknown founder {founder_id}")
    company = next((p.strip() for p in reversed(row["name"].split("/")) if p.strip()),
                   row["name"])
    queries = [f"{company} market size category",
               f"{company} competitors alternatives comparison"]
    cat = _category_of(conn, founder_id, company, replay=replay)
    if cat:
        queries += [f"{cat} market size TAM forecast",
                    f"{cat} market growth rate vendors market share"]
    return queries


def enrich_market(conn, founder_id: str, *, replay: bool) -> list[dict]:
    """Tavily market research: TAM / competitors / comparable rounds -> ingested as
    tavily signals so the EXISTING market and risk workers extract external,
    externally-cited market claims through the same corroboration tiering. Novel
    founders only (fixtures are fictional — nothing to research, and determinism)."""
    if founder_id in FIXTURE_FOUNDER_IDS:
        raise ValueError(f"market research refused for fixture founder {founder_id} "
                         "(fictional company; demo determinism guardrail)")
    found: list[dict] = []
    ranked: list[tuple[float, str]] = []
    for q in _market_queries(conn, founder_id, replay=replay):
        resp = tavily.web_search(q, replay=replay)
        for r in resp.get("results", []):
            if not r.get("url"):
                continue
            dom = domain_of(r["url"])
            # Provenance is explicit in the signal itself: a single third-party web
            # page is not corroboration. This keeps the market/risk workers from
            # laundering a scraped estimate into a high-trust "corroborated" claim.
            ingest.ingest_signal(conn, Signal(
                source="tavily", source_url=r["url"],
                content=f"[market research · UNVERIFIED third-party web source ({dom}) "
                        f"· query: {q}] {r.get('title', '')} | {r.get('content', '')}",
                observed_at=r.get("published_date"), founder_id=founder_id))
            ranked.append((r.get("score", 0.0), r["url"]))
            found.append({"query": q, "title": r.get("title"), "url": r["url"]})
    top = [u for _, u in sorted(ranked, reverse=True)[:4]]
    if top:
        ext = tavily.extract(top, replay=replay)
        for r in ext.get("results", []):
            if r.get("raw_content"):
                # Keep the market-research tag on extracted page bodies too, so the
                # founder-scoping filter and news-worker gate both exclude them.
                ingest.ingest_signal(conn, Signal(
                    source="tavily", source_url=r["url"],
                    content=f"[market research · extracted page ({domain_of(r['url'])})] "
                            f"{r['raw_content'][:4000]}", founder_id=founder_id))
    return found


def run_diligence(conn, founder_id: str, thesis, *, replay: bool,
                  news: bool = False, market: bool = False) -> dict:
    """news/market=True add Tavily enrichment stages before the workers run.
    ONLY safe for novel founders (new inbound applies): they append signals, which
    changes worker evidence and llm cache keys. Fixture founders are always skipped,
    and the defaults stay False so replay/rebuild paths are untouched."""
    lens = thesis_mod.lens(thesis)
    if news and founder_id not in FIXTURE_FOUNDER_IDS:
        try:
            with instrument.stage(conn, founder_id, "news"):
                enrich_news(conn, founder_id, replay=replay)
        except (RuntimeError, cache.ReplayMiss) as e:
            print(f"[news] enrichment skipped for {founder_id}: {e}")
    if market and founder_id not in FIXTURE_FOUNDER_IDS:
        try:
            with instrument.stage(conn, founder_id, "market"):
                enrich_market(conn, founder_id, replay=replay)
        except (RuntimeError, cache.ReplayMiss) as e:
            print(f"[market] research skipped for {founder_id}: {e}")
    evidence = loader.founder_evidence(conn, founder_id)
    # Founder/traction workers get the market-research pages removed (see loader):
    # a competitor page is not evidence about the founder, and feeding it to the
    # integrity check manufactures false contradictions on real people.
    founder_ev = loader.founder_evidence(conn, founder_id, kind="founder")

    # 1. Workers extract claims (grounded, non-adversarial). Drafts without a
    # resolvable evidence URL are dropped + reported, never stored or patched.
    with instrument.stage(conn, founder_id, "extract"):
        claims, dropped_claims = ledger.assemble(
            workers.extract_all(evidence, replay=replay, founder_evidence=founder_ev))
    for d in dropped_claims:
        print(f"[ledger] dropped draft {d['id']}: {d['reason']}")
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
            "memo": memo, "violations": viol, "dropped_claims": dropped_claims}
