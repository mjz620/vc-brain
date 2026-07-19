"""Tavily evidence layer: replay from seeded cache with NO key, budget cap,
fixture-founder refusal, and tavily signals flowing into founder_evidence.
All content here is clearly synthetic ("Smoke Test Co") — no live network calls."""
import json

import pytest
from fastapi import HTTPException

from app import cache, config
from app.diligence import loader, pipeline, workers
from app.memory import db, ingest
from app.memory.models import Founder, Signal
from app.sources import tavily

URL1 = "https://example.com/smoke-test-co-seed"
URL2 = "https://example.com/smoke-test-co-launch"


def _seed(namespace, payload, data):
    key = cache._key(namespace, payload)
    p = config.CACHE_DIR / namespace / f"{key}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data))


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    conn = db.connect(":memory:")
    db.init_db(conn)
    ingest.upsert_founder(conn, Founder(id="founder-smoketest",
                                        name="Sam Tester / Smoke Test Co"))
    return conn


def _search_fixture(q, url, score):
    return {"query": q, "results": [{
        "title": "Smoke Test Co (synthetic fixture article)", "url": url,
        "content": "Synthetic fixture: the fictional Smoke Test Co did a fictional thing.",
        "score": score}], "response_time": 0.1}


def test_replay_from_cache_needs_no_key(env):
    q = "Smoke Test Co news"
    _seed("tavily_search", {"query": q, "topic": "news", "max_results": 6},
          _search_fixture(q, URL1, 0.9))
    resp = tavily.news_search(q, replay=True)  # no key set: cache hit only
    assert resp["results"][0]["url"] == URL1
    with pytest.raises(cache.ReplayMiss):
        tavily.news_search("uncached query", replay=True)


def test_budget_cap_refuses_live_call(env, monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-fake-for-test")
    config.CACHE_DIR.joinpath("tavily_spend.json").write_text(json.dumps(
        {"month": tavily.spend_state()["month"], "credits": tavily.HARD_CAP}))
    with pytest.raises(RuntimeError, match="budget cap"):
        tavily.news_search("never cached", replay=False)


def test_enrich_endpoint_refuses_fixture_founders(env):
    from app.api import evidence

    class _Req:  # minimal stand-in for fastapi.Request (ratelimit reads these)
        headers = {}
        client = None

    for fid in pipeline.FIXTURE_FOUNDER_IDS:
        with pytest.raises(HTTPException) as e:
            evidence.enrich(fid, _Req())
        assert e.value.status_code == 409
    assert pipeline.FIXTURE_FOUNDER_IDS == {
        "founder-tracewell", "founder-corevance", "founder-parcelmind"}


def test_enrich_news_ingests_signals_into_founder_evidence(env):
    conn = env
    q1 = "Sam Tester Smoke Test Co"
    q2 = "Smoke Test Co startup funding"
    _seed("tavily_search", {"query": q1, "topic": "news", "max_results": 6},
          _search_fixture(q1, URL1, 0.9))
    _seed("tavily_search", {"query": q2, "topic": "news", "max_results": 6},
          _search_fixture(q2, URL2, 0.8))
    _seed("tavily_extract", {"urls": sorted([URL1, URL2])},
          {"results": [{"url": URL1, "raw_content": "Synthetic fixture body text."}],
           "failed_results": [{"url": URL2, "error": "fixture"}]})

    found = pipeline.enrich_news(conn, "founder-smoketest", replay=True)
    assert {f["url"] for f in found} == {URL1, URL2}

    ev = loader.founder_evidence(conn, "founder-smoketest")
    assert "[tavily]" in ev and URL1 in ev
    assert "Synthetic fixture body text." in ev  # extract content reached evidence
    # fixture founders are hard-refused even when called directly
    with pytest.raises(ValueError):
        pipeline.enrich_news(conn, "founder-corevance", replay=True)


def test_news_worker_gated_on_tavily_signals(monkeypatch):
    ran = []
    monkeypatch.setattr(workers, "run_worker",
                        lambda ev, axis, prefix, focus, replay: ran.append(axis) or [])
    workers.extract_all("[deck] source_url=file://d\ncontent", replay=True)
    assert "news" not in ran and len(ran) == 4
    ran.clear()
    workers.extract_all("[tavily] source_url=https://example.com/a\narticle", replay=True)
    assert "news" in ran and len(ran) == 5
