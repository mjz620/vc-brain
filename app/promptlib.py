"""Prompt loader with a human-owned override.

Worker prompts and scoring rubrics live in `prompts/` and are HUMAN-OWNED (CLAUDE.md
guardrail): they ship as `# TODO(mingjia)` stubs for the human to iterate by hand. Until
a stub is filled with real content, the code falls back to an embedded minimal default so
the block is runnable. Filling `prompts/<name>.md` takes over — the default is scaffolding,
not the tuned rubric.
"""
from . import config


def load_prompt(name: str, default: str) -> str:
    path = config.ROOT / "prompts" / f"{name}.md"
    if path.exists():
        txt = path.read_text()
        # A stub contains only comment/TODO lines; treat non-comment content as "filled".
        body = "\n".join(l for l in txt.splitlines()
                         if l.strip() and not l.strip().startswith("#")).strip()
        if body:
            return txt.strip()
    return default
