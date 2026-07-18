"""HTTP fetch helpers, cached to the replay store.

Every live response is cached keyed by (url, params). Replay mode reads only from
cache — a miss is a hard error — so the demo is deterministic (spec §8).
"""
from urllib.parse import urlparse

import httpx

from .. import cache

_UA = {"User-Agent": "vc-brain/0.1 (hackathon)"}


def get_json(url: str, params: dict, *, replay: bool):
    def producer():
        r = httpx.get(url, params=params, headers=_UA, timeout=25,
                      follow_redirects=True)
        r.raise_for_status()
        return r.json()
    return cache.cached("http", {"url": url, "params": params}, producer, replay=replay)


def get_text(url: str, params: dict, *, replay: bool):
    def producer():
        r = httpx.get(url, params=params, headers=_UA, timeout=25,
                      follow_redirects=True)
        r.raise_for_status()
        return r.text
    return cache.cached("http_text", {"url": url, "params": params}, producer,
                        replay=replay)


def domain_of(url: str | None) -> str:
    if not url:
        return ""
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host
