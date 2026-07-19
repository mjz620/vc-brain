"""The integrity gate's input is fully determined by the ledger, so a pass justified
by an integrity failure the ledger does not contain is wrong by construction.

This was live: four of six stored decisions passed citing "multiple contradicted
claims" against ledgers holding zero. The tier-count line omitted zero-count tiers,
so on a clean ledger the word "contradicted" never reached the judge at all.
"""
from app.diligence import debate
from app.diligence.schemas import Recommendation
from app.memory.models import Claim


def _claim(cid, axis, corroboration):
    return Claim(id=cid, axis=axis, text=f"{cid} text", stance="supports",
                 evidence="snip", evidence_url="https://example.com/x",
                 source_type="deck", corroboration=corroboration, trust=0.4)


def _rec(decision, rationale):
    return Recommendation(decision=decision, amount_usd=0, claims_it_turns_on=["team-01"],
                          what_would_change_our_mind="a filing appears",
                          open_items=[], rationale=rationale)


CLEAN = [_claim("team-01", "founder", "self_reported"),
         _claim("trac-01", "traction", "corroborated")]
CONTRADICTED = CLEAN + [_claim("team-02", "founder", "contradicted")]
# A disproved risk hypothesis is not a founder integrity failure — the prompt excludes it.
RISK_ONLY = CLEAN + [_claim("risk-01", "risk", "contradicted")]


def test_gate_counts_only_founder_assertions():
    assert debate.integrity_gate_count(CLEAN) == 0
    assert debate.integrity_gate_count(CONTRADICTED) == 1
    assert debate.integrity_gate_count(RISK_ONLY) == 0


def test_brief_states_zero_tiers_and_the_gate_verdict():
    brief = debate._ledger_brief(CLEAN)
    # The regression: "contradicted" must appear even when the count is zero.
    assert "contradicted=0" in brief
    assert "THE INTEGRITY GATE CANNOT FIRE" in brief

    fired = debate._ledger_brief(CONTRADICTED)
    assert "contradicted=1" in fired
    assert "CANNOT FIRE" not in fired


def test_phantom_gate_detects_only_the_real_error():
    phantom = _rec("pass", "The integrity gate fires: multiple contradicted claims.")
    assert debate._phantom_gate(phantom, 0) is True

    # Legitimate structural pass — never mentions contradictions.
    structural = _rec("pass", "No evidence of a market or a shipped product at this stage.")
    assert debate._phantom_gate(structural, 0) is False

    # Same language, but the contradictions are real.
    grounded = _rec("pass", "Six contradicted claims including the acquisition record.")
    assert debate._phantom_gate(grounded, 6) is False

    # Not a pass — conditional/invest are out of scope for this guard.
    assert debate._phantom_gate(_rec("conditional", "contradicted"), 0) is False


def test_retry_then_annotate_when_the_judge_repeats_the_error(monkeypatch):
    calls = []

    def fake(tier, system, user, schema, *, replay, max_tokens=1024):
        calls.append(user)
        if schema is Recommendation:
            return _rec("pass", "Integrity gate fires on contradicted founder claims.")
        return schema(argument="[team-01] argued")
    monkeypatch.setattr(debate.llm, "call", fake)

    rec, _, _ = debate.run_debate(CLEAN, "thesis lens", replay=True)
    # Re-asked once with the mechanical correction...
    assert any("MECHANICAL CORRECTION" in c for c in calls)
    # ...and when the judge repeated itself, the output carries the discrepancy.
    assert "validator:" in rec.rationale
    assert "did not fire" in rec.rationale
