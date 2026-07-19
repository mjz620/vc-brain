"""Central config: paths, model tiers, replay toggle."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")  # keys for the server/CLI; real env vars win (override=False)
DB_PATH = ROOT / "vc_brain.db"
CACHE_DIR = ROOT / "app" / "cache"
FIXTURES = ROOT / "fixtures"

# Model tiers (confirmed with user). Cheap kill screen + entity-resolution aid on
# Haiku; diligence workers on Sonnet; synthesizer + critic on Opus.
MODEL_TIERS = {
    "screen": "claude-haiku-4-5",
    "resolve": "claude-haiku-4-5",
    "worker": "claude-sonnet-5",
    "synth": "claude-opus-4-8",
    "critic": "claude-opus-4-8",
}

# OpenAI model tiers (used when OPENAI_API_KEY is present). Env-overridable so you can
# point tiers at whatever your account has, without touching code:
#   OPENAI_MODEL=<id>                       -> one model for every tier
#   OPENAI_MODEL_SCREEN / _WORKER / _SYNTH  -> per-tier override
_OPENAI_DEFAULTS = {"screen": "gpt-4o-mini", "resolve": "gpt-4o-mini",
                    "worker": "gpt-4o-mini", "synth": "gpt-4o", "critic": "gpt-4o"}
_OPENAI_ENV = {"screen": "OPENAI_MODEL_SCREEN", "resolve": "OPENAI_MODEL_SCREEN",
               "worker": "OPENAI_MODEL_WORKER", "synth": "OPENAI_MODEL_SYNTH",
               "critic": "OPENAI_MODEL_SYNTH"}


def openai_model(tier: str) -> str:
    if all_models := os.environ.get("OPENAI_MODEL"):
        return all_models
    env_key = _OPENAI_ENV.get(tier)
    return (os.environ.get(env_key) if env_key else None) or _OPENAI_DEFAULTS.get(tier, "gpt-4o")


# Reference "today" for the demo fixtures (spec §4).
DEMO_TODAY = "2026-07-18"


def replay_enabled(flag: bool | None = None) -> bool:
    """Replay = read only from cache, never make a live call. Flag overrides env."""
    if flag is not None:
        return flag
    return os.environ.get("VC_REPLAY", "0") == "1"
