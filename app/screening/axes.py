"""Three-axis screening (spec §2.3, brief FAQ 5): Founder, Market, Idea-vs-Market.

The axes are scored **independently and never averaged**. Each carries a trend arrow
(improving/declining/stable, or "new" on first score) computed from the append-only
axis_scores history. The disagreement between axes IS the display.
"""
from datetime import datetime, timezone

from pydantic import BaseModel

from .. import llm
from ..promptlib import load_prompt
from . import thesis as thesis_mod

AXES = ("founder", "market", "idea")

# Embedded minimal defaults; replaced by prompts/rubric_<axis>.md once filled.
_DEFAULTS = {
    "founder": ("Score the FOUNDER axis 0-10 for a venture opportunity. Weight observable "
                "execution velocity (shipping cadence, iteration, public footprint) over "
                "pedigree — a thin but fast-moving record can score high. stance in "
                "{strong, mixed, weak}."),
    "market": ("Score the MARKET axis 0-10. Assess sizing and competitive dynamics. "
               "stance in {bullish, neutral, bear}."),
    "idea": ("Score the IDEA-VS-MARKET axis 0-10: does the idea survive scrutiny as-is, "
             "or is this a bet on the team's ability to pivot? stance in "
             "{survives, pivot-bet, weak}."),
}
_COMMON = (" Also return coverage 0-1 (how much verifiable evidence backs this, low for "
           "cold-start records) and a one-line rationale that references the fund thesis.")


class AxisAssessment(BaseModel):
    score: float
    stance: str
    coverage: float
    rationale: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def founder_summary(conn, founder_id: str) -> str:
    """Assemble a founder's resolved signals + entity keys into a scoring summary."""
    row = conn.execute("SELECT name, entity_keys FROM founders WHERE id=?",
                       (founder_id,)).fetchone()
    keys = row["entity_keys"] if row else "{}"
    sigs = conn.execute(
        "SELECT s.source, s.content FROM signals s "
        "LEFT JOIN resolutions r ON r.signal_id = s.id "
        "WHERE r.founder_id = ? OR s.founder_id = ?", (founder_id, founder_id)).fetchall()
    lines = [f"- [{s['source']}] {s['content']}" for s in sigs]
    # Persistent Founder Score is ONE INPUT into the Founder axis, not a substitute
    # for the per-opportunity score (brief FAQ 6).
    from ..memory import founder_score as fs_mod
    fs = fs_mod.stored(conn, founder_id)
    fs_line = ""
    if fs:
        latest = fs["history"][-1]
        fs_line = (f"Persistent Founder Score (cross-application input, distinct from "
                   f"this screen): {latest['score']}/10, dimensions {fs.get('dimensions')}, "
                   f"record coverage {fs.get('coverage', 0):.0%}, "
                   f"{len(fs['history'])} history points\n")
    return (f"Founder: {row['name'] if row else founder_id}\nEntity keys: {keys}\n"
            f"{fs_line}Signals ({len(lines)}):\n" + "\n".join(lines))


def score_axis(conn, founder_id: str, axis: str, thesis: thesis_mod.Thesis,
               summary: str, *, replay: bool) -> AxisAssessment:
    system = load_prompt(f"rubric_{axis}", _DEFAULTS[axis] + _COMMON)
    user = f"{thesis_mod.lens(thesis)}\n\n--- Opportunity summary ---\n{summary}"
    a = llm.call("worker", system, user, AxisAssessment, replay=replay, max_tokens=400)
    conn.execute(
        "INSERT INTO axis_scores (founder_id, axis, score, stance, rationale, "
        "coverage, thesis, scored_at) VALUES (?,?,?,?,?,?,?,?)",
        (founder_id, axis, a.score, a.stance, a.rationale, a.coverage,
         thesis.name, _now()))
    conn.commit()
    return a


def trend(conn, founder_id: str, axis: str) -> str:
    """improving / declining / stable from the last two scores; 'new' if only one."""
    rows = conn.execute(
        "SELECT score FROM axis_scores WHERE founder_id=? AND axis=? "
        "ORDER BY scored_at DESC LIMIT 2", (founder_id, axis)).fetchall()
    if len(rows) < 2:
        return "new"
    latest, prev = rows[0]["score"], rows[1]["score"]
    if latest > prev + 0.3:
        return "improving"
    if latest < prev - 0.3:
        return "declining"
    return "stable"


def screen(conn, founder_id: str, thesis: thesis_mod.Thesis, *, replay: bool) -> dict:
    """Run the full screen: kill screen, then 3 independent axes + trends.

    Returns a dict with the three axes side by side. There is deliberately NO blended
    or averaged score field — collapsing the axes hides the disagreement (brief FAQ 5).
    """
    from .firstpass import first_pass, log_kill
    summary = founder_summary(conn, founder_id)
    fp = first_pass(summary, thesis_mod.lens(thesis), replay=replay)
    if not fp.viable:
        log_kill(conn, founder_id, fp.reason, thesis.name)
        return {"founder_id": founder_id, "thesis": thesis.name, "killed": True,
                "kill_reason": fp.reason}

    axes = {}
    for axis in AXES:
        a = score_axis(conn, founder_id, axis, thesis, summary, replay=replay)
        axes[axis] = {"score": a.score, "stance": a.stance, "coverage": a.coverage,
                      "rationale": a.rationale, "trend": trend(conn, founder_id, axis)}
    return {"founder_id": founder_id, "thesis": thesis.name, "killed": False,
            "axes": axes}  # note: no composite/average key by design
