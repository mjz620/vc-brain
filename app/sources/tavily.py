"""Tavily client (challenge sponsor): open-web founder research, replay-cached.

Both calls route through app.cache.cached exactly like app/sources/http.py, so
replay stays deterministic and every credit is spent at most once per unique
request. A persisted per-month spend counter enforces a hard cap well under the
1000-credit free tier.

API surface (verified against docs.tavily.com, 2026-07-18):
  TavilyClient(api_key).search(query, topic="news", max_results=n)
      -> {"results": [{"title", "url", "content", "score", ...}], ...}
  TavilyClient(api_key).extract(urls)
      -> {"results": [{"url", "raw_content"}], "failed_results": [...]}
Credits: search(basic) = 1; extract(basic) = 1 per 5 successful URLs.
"""
import json
import math
import os
from datetime import datetime, timezone

from .. import cache, config

HARD_CAP = 900  # credits per calendar month; refuse live calls beyond this


def _spend_path():
    return config.CACHE_DIR / "tavily_spend.json"


def spend_state() -> dict:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    p = _spend_path()
    state = {"month": month, "credits": 0}
    if p.exists():
        saved = json.loads(p.read_text())
        if saved.get("month") == month:
            state = saved
    return state


def _check_cap(credits: int) -> None:
    state = spend_state()
    if state["credits"] + credits > HARD_CAP:
        raise RuntimeError(
            f"Tavily budget cap: {state['credits']}/{HARD_CAP} credits used in "
            f"{state['month']}; refusing a live call for {credits} more")


def _record(credits: int) -> None:
    state = spend_state()
    state["credits"] += credits
    p = _spend_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state))


def _client():
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("TAVILY_API_KEY not set and no cached response for this "
                           "request — set the key or run against seeded cache")
    from tavily import TavilyClient
    return TavilyClient(api_key=key)


def news_search(query: str, *, replay: bool, max_results: int = 6) -> dict:
    """News search. 1 credit live; free on cache hit / replay."""
    def producer():
        _check_cap(1)
        resp = _client().search(query, topic="news", max_results=max_results)
        _record(1)
        return resp
    return cache.cached("tavily_search", {"query": query, "topic": "news",
                                          "max_results": max_results},
                        producer, replay=replay)


def extract(urls: list[str], *, replay: bool) -> dict:
    """Extract page content for `urls`. 1 credit per 5 URLs live; free on cache hit."""
    urls = sorted(urls)
    def producer():
        credits = math.ceil(len(urls) / 5)
        _check_cap(credits)
        resp = _client().extract(urls)
        _record(credits)
        return resp
    return cache.cached("tavily_extract", {"urls": urls}, producer, replay=replay)
