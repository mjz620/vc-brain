"""Anthropic wrapper: model-tier select + structured output + replay cache.

Every call is cached keyed by (model, system, user, schema). Replay reads only from
cache, so the demo makes zero live calls. The client is constructed lazily, so replay
and tests run with no ANTHROPIC_API_KEY present.
"""
from typing import Type, TypeVar

from pydantic import BaseModel

from . import cache, config

_client = None
T = TypeVar("T", bound=BaseModel)


def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic()
    return _client


def call(tier: str, system: str, user: str, schema: Type[T], *, replay: bool,
         max_tokens: int = 1024) -> T:
    """Structured-output call on the given model tier, returning a `schema` instance."""
    model = config.MODEL_TIERS[tier]
    payload = {"model": model, "system": system, "user": user,
               "schema": schema.__name__, "fields": sorted(schema.model_fields)}

    def producer():
        resp = _get_client().messages.parse(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}], output_format=schema)
        return resp.parsed_output.model_dump()

    data = cache.cached("llm", payload, producer, replay=replay)
    return schema(**data)
