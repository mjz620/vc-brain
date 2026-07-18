"""Central config: paths, model tiers, replay toggle."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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

# Reference "today" for the demo fixtures (spec §4).
DEMO_TODAY = "2026-07-18"


def replay_enabled(flag: bool | None = None) -> bool:
    """Replay = read only from cache, never make a live call. Flag overrides env."""
    if flag is not None:
        return flag
    return os.environ.get("VC_REPLAY", "0") == "1"
