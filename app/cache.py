"""Replay cache scaffold.

Every live response (HTTP source fetch or LLM call) is cached to disk keyed by a hash
of its request. In replay mode we read only from cache and never make a live call — a
cache miss under replay is a hard error, which is what makes the demo deterministic
(spec §8: anything shown in the demo runs from cached/replay state).

Used by the source adapters (Block 2) and the LLM wrapper (Block 4).
"""
import hashlib
import json
from pathlib import Path
from typing import Callable

from . import config


class ReplayMiss(Exception):
    """Raised when replay is on but no cached response exists for the request."""


def _key(namespace: str, payload) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(f"{namespace}\x00{blob}".encode()).hexdigest()


def cached(namespace: str, payload, producer: Callable[[], object], *, replay: bool):
    """Return cached response for `payload`, else produce + cache it (unless replay)."""
    key = _key(namespace, payload)
    path: Path = config.CACHE_DIR / namespace / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    if replay:
        raise ReplayMiss(f"no cached {namespace} response for {key[:12]} (replay mode)")
    result = producer()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, default=str))
    return result
