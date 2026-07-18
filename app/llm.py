"""Provider-agnostic LLM wrapper: OpenAI or Anthropic + structured output + replay cache.

Backend auto-selects on the key present: OpenAI when OPENAI_API_KEY is set, else
Anthropic. Both return a validated `schema` instance. The cache key is LOGICAL
(tier + prompt + schema) — independent of provider/model — so a cache seeded live with
one provider replays deterministically with NO key present. Clients are lazily built,
so replay/tests need no key at all.
"""
import os
from typing import Type, TypeVar

from pydantic import BaseModel

from . import cache, config

T = TypeVar("T", bound=BaseModel)
_oai = None
_ant = None


def provider() -> str | None:
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return "anthropic"
    return None


def _openai_call(model, system, user, schema, max_tokens):
    global _oai
    if _oai is None:
        from openai import OpenAI
        _oai = OpenAI()
    completion = _oai.beta.chat.completions.parse(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        response_format=schema,
        max_completion_tokens=max_tokens,
    )
    return completion.choices[0].message.parsed.model_dump()


def _anthropic_call(model, system, user, schema, max_tokens):
    global _ant
    if _ant is None:
        from anthropic import Anthropic
        _ant = Anthropic()
    resp = _ant.messages.parse(model=model, max_tokens=max_tokens, system=system,
                               messages=[{"role": "user", "content": user}],
                               output_format=schema)
    return resp.parsed_output.model_dump()


def call(tier: str, system: str, user: str, schema: Type[T], *, replay: bool,
         max_tokens: int = 1024) -> T:
    payload = {"tier": tier, "system": system, "user": user,
               "schema": schema.__name__, "fields": sorted(schema.model_fields)}

    def producer():
        p = provider()
        if p == "openai":
            return _openai_call(config.openai_model(tier), system, user, schema, max_tokens)
        if p == "anthropic":
            return _anthropic_call(config.MODEL_TIERS[tier], system, user, schema, max_tokens)
        raise RuntimeError("no LLM key set (OPENAI_API_KEY or ANTHROPIC_API_KEY) and no "
                           "cached response for this request")

    data = cache.cached("llm", payload, producer, replay=replay)
    return schema(**data)
