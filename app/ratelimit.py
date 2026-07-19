"""Per-IP fixed-window rate limiting for the expensive interactive endpoints.

In-memory on purpose: one free-tier instance, and the budget being protected is
LLM/API spend, not distributed abuse. A judge can drive the demo; a loop cannot
drain the key. Returns 429 with an honest, human-readable message.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

# endpoint label -> (max calls, window seconds)
LIMITS = {
    "apply": (3, 3600),   # each apply can cost 13-31 LLM calls
    "diligence": (4, 3600),  # forced screen->diligence, same LLM cost as apply
    "scan": (6, 3600),    # live source fetches
    "query": (10, 60),
    "activate": (6, 3600),
    "enrich": (4, 3600),  # Tavily credits
    "ask": (12, 60),
}

_hits: dict[tuple[str, str], deque] = defaultdict(deque)


def check(label: str, request: Request) -> None:
    """Raise 429 if this client exceeded the window for `label`."""
    limit, window = LIMITS[label]
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else "?"))
    q = _hits[(label, ip)]
    now = time.monotonic()
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        mins = int(window / 60)
        raise HTTPException(429, f"rate limit: {limit} {label} calls per {mins} min "
                                 "per client — this endpoint spends real API budget")
    q.append(now)
