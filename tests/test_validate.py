"""Block 4 gate item 2: the mechanical validator rejects a memo sentence AND a debate
turn that cite a fake claim ID. No LLM, runs with no key."""
from app.diligence import validate as v

VALID = {"team-02", "trac-01", "dd-02", "prod-10", "open-03"}


def test_real_citations_pass():
    text = ("Execution velocity is strong [team-02]. Repo is 9 weeks old with 1,420 "
            "stars [trac-01].")
    viol = v.validate(text, VALID)
    assert viol.ok
    assert viol.unknown_ids == []


def test_fake_claim_id_in_memo_is_rejected():
    text = "Claimed $480K ARR is corroborated [trac-99]."  # trac-99 not in ledger
    viol = v.validate(text, VALID)
    assert "trac-99" in viol.unknown_ids
    assert not viol.ok


def test_fake_claim_id_in_debate_turn_is_rejected():
    turn = "I argue invest: the founder shipped fast [team-02] and it replicated [team-77]."
    viol = v.validate_turn(turn, VALID)
    assert viol.unknown_ids == ["team-77"]
    assert not viol.ok


def test_uncited_quantitative_assertion_is_advisory():
    text = "The company has 14 customers and $480K ARR."  # numbers, no citation
    viol = v.validate(text, VALID)
    assert viol.uncited_quant       # surfaced as an advisory signal
    assert viol.ok                  # but does NOT hard-fail: only fake claim ids do


def test_gap_flag_line_is_not_flagged():
    # brief's own gap phrasing carries numbers-adjacent text but is not an assertion
    text = "Cap table: not disclosed. Financials: not applicable at this stage."
    viol = v.validate(text, VALID)
    assert viol.uncited_quant == []
    assert viol.ok


def test_trust_tier_notation_parses_as_one_citation():
    text = "No Form D for the claimed seed [dd-02 · 0.9 · corr — EDGAR search, negative]."
    assert v.citations(text) == {"dd-02"}
    assert v.validate(text, VALID).ok
