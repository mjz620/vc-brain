"""First-pass kill screen (spec §2.3): a single cheap model call (Haiku) that removes
clearly non-viable opportunities before full analysis. The kill reason is logged."""
from datetime import datetime, timezone

from pydantic import BaseModel

from .. import llm
from ..promptlib import load_prompt

# Embedded minimal default — replaced by prompts/screen_first_pass.md once the human
# fills it (see promptlib). Scaffolding, not the tuned rubric.
_DEFAULT = (
    "You are a fast first-pass screener for a venture fund. Given a founder/company "
    "summary and the fund thesis, decide if the opportunity is CLEARLY non-viable "
    "(e.g. wrong sector for the thesis, no real product or signal, incoherent). Be "
    "permissive: only kill obvious non-starters — full diligence handles the rest. "
    "Return viable=true/false and a one-line reason."
)


class FirstPass(BaseModel):
    viable: bool
    reason: str


def first_pass(summary: str, thesis_lens: str, *, replay: bool) -> FirstPass:
    system = load_prompt("screen_first_pass", _DEFAULT)
    user = f"{thesis_lens}\n\n--- Opportunity summary ---\n{summary}"
    return llm.call("screen", system, user, FirstPass, replay=replay, max_tokens=256)


def log_kill(conn, founder_id: str, reason: str, thesis_name: str) -> None:
    conn.execute("INSERT INTO kill_log (founder_id, reason, thesis, logged_at) "
                 "VALUES (?,?,?,?)",
                 (founder_id, reason, thesis_name,
                  datetime.now(timezone.utc).isoformat()))
    conn.commit()
