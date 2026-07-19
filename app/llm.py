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


# Generous connect/read timeout + retries: free-tier hosts (0.1 CPU) blow the SDK's
# default 5s connect timeout and surface it as an opaque "APIConnectionError". An
# explicit longer timeout with retries turns those flakes into successful calls.
_TIMEOUT = float(os.environ.get("VC_LLM_TIMEOUT", "60"))
_RETRIES = int(os.environ.get("VC_LLM_RETRIES", "4"))


def _openai_call(model, system, user, schema, max_tokens):
    global _oai
    if _oai is None:
        from openai import OpenAI
        _oai = OpenAI(timeout=_TIMEOUT, max_retries=_RETRIES)
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
        _ant = Anthropic(timeout=_TIMEOUT, max_retries=_RETRIES)
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
        if p is None:
            raise RuntimeError("no LLM key set (OPENAI_API_KEY or ANTHROPIC_API_KEY) "
                               "and no cached response for this request")
        try:
            if p == "openai":
                return _openai_call(config.openai_model(tier), system, user, schema,
                                    max_tokens)
            return _anthropic_call(config.MODEL_TIERS[tier], system, user, schema,
                                   max_tokens)
        except Exception as e:
            # The OpenAI/Anthropic SDKs collapse network failures into an opaque
            # "Connection error." — surface the real underlying cause (DNS, TLS,
            # timeout, refused) so a deploy failure is diagnosable, not a mystery.
            cause = e.__cause__ or getattr(e, "__context__", None)
            if cause:
                raise RuntimeError(
                    f"{type(e).__name__}: {e} [cause: {type(cause).__name__}: "
                    f"{cause}]") from e
            raise

    data = cache.cached("llm", payload, producer, replay=replay)
    return schema(**data)
