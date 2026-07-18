"""Activate: outreach draft for a high-conviction outbound founder (brief MVP 5).

"Cold outreach, not cold investment" — the goal is to trigger a real application. The
draft must cite the specific signal that triggered it; a mechanical check rejects any
draft whose citation is not the actual triggering signal URL (no-fabrication guardrail).
"""
from datetime import datetime, timezone

from pydantic import BaseModel

from . import llm
from .promptlib import load_prompt

_DEFAULT = (
    "Draft a short cold outreach email (<=120 words) from a pre-seed fund to a founder "
    "surfaced by an outbound scanner. Rules: reference ONLY facts present in the "
    "triggering signal provided; cite it concretely (name the repo/post/launch); no "
    "flattery padding, no investment promise — invite them to apply/share materials. "
    "Set cited_signal_url to exactly the triggering signal URL you were given.")


class OutreachDraft(BaseModel):
    subject: str
    body: str
    cited_signal_url: str


def triggering_signal(conn, founder_id: str):
    """The founder's most recent resolved signal — the one that put them over the bar."""
    return conn.execute(
        "SELECT s.* FROM signals s JOIN resolutions r ON r.signal_id = s.id "
        "WHERE r.founder_id = ? "
        "ORDER BY COALESCE(s.observed_at, s.ingested_at) DESC LIMIT 1",
        (founder_id,)).fetchone()


def draft(conn, founder_id: str, thesis_name: str, *, replay: bool) -> OutreachDraft:
    sig = triggering_signal(conn, founder_id)
    if sig is None:
        raise ValueError(f"no resolved signals for {founder_id} — nothing to cite")
    row = conn.execute("SELECT name FROM founders WHERE id=?", (founder_id,)).fetchone()
    system = load_prompt("activate", _DEFAULT)
    user = (f"Fund: {thesis_name}\nFounder handle: {row['name']}\n"
            f"Triggering signal ({sig['source']}): {sig['content']}\n"
            f"Signal URL: {sig['source_url']}")
    d = llm.call("worker", system, user, OutreachDraft, replay=replay, max_tokens=400)
    if d.cited_signal_url != sig["source_url"]:
        raise ValueError(f"outreach draft cited {d.cited_signal_url!r}, not the "
                         f"triggering signal {sig['source_url']!r} — rejected")
    conn.execute(
        "INSERT OR REPLACE INTO outreach (founder_id, signal_id, subject, body, "
        "created_at) VALUES (?,?,?,?,?)",
        (founder_id, sig["id"], d.subject, d.body,
         datetime.now(timezone.utc).isoformat()))
    conn.commit()
    return d
