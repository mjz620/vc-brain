"""Block 4 pipeline wiring (mocked LLM, no key). Proves: contested claims are adjudicated
and the Judge's trust OVERRIDES the rubric (gate item 3); a memo is produced and stored;
the validator runs on it."""
import re

import pytest

from app import llm
from app.diligence import ledger, pipeline
from app.memory import db
from app.screening import thesis as th


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_db(c)
    return c


def _fake_call(tier, system, user, schema, *, replay, max_tokens=1024):
    n = schema.__name__
    if n == "WorkerOutput":
        prefix = (re.search(r"id prefix '([a-z]+)-'", user) or [None, "gen"])[1]
        # founder -> a contradicted claim; traction -> self_reported; else single_source
        corr = {"team": "contradicted", "trac": "self_reported"}.get(prefix, "single_source")
        return schema(claims=[{
            "id": f"{prefix}-01", "axis": "founder" if prefix == "team" else "market",
            "text": f"{prefix} claim with a value of 480 units", "stance": "supports",
            "evidence": "snippet", "source_url": "https://x.example", "source_type": "web",
            "corroboration": corr, "observed_at": "2026-07-18"}])
    if n == "Argument":
        return schema(argument="I rely on [team-01] and [trac-01].")
    if n == "Verdict":  # distinct trust 0.25 so we can prove Judge override (rubric would be 0.3/0.4)
        return schema(corroboration="contradicted", trust=0.25, stance="contradicts",
                      rationale="external record conflicts with the claim")
    if n == "Recommendation":
        return schema(decision="pass", amount_usd=100000, claims_it_turns_on=["team-01"],
                      what_would_change_our_mind="reference checks resolve both contradictions",
                      open_items=["confirm timeline"], rationale="integrity dimension caps it")
    if n == "MemoOut":
        return schema(markdown=("## ⚠ Contradictions found — read first\n"
                                "The exit claim fails verification [team-01 · 0.25 · contradicted].\n\n"
                                "## Recommendation\nPass [team-01]. Cap table: not disclosed.\n"))
    if n == "CriticResult":
        return schema(supported=True, issues=[], revised_markdown="")
    raise AssertionError(f"unexpected schema {n}")


def test_pipeline_adjudicates_and_judge_sets_trust(conn, monkeypatch):
    monkeypatch.setattr(llm, "call", _fake_call)
    from app.diligence import loader
    fid = loader.load_fixture(conn, "founder_b_corevance", replay=True)
    thesis = th.load_thesis("config/thesis_preseed_ai_infra.yaml")
    result = pipeline.run_diligence(conn, fid, thesis, replay=True)

    assert result["claims"] >= 1
    assert result["contested"] >= 1                 # contradicted/self_reported went to adjudication
    assert result["recommendation"].decision == "pass"

    # gate item 3: the contested claim's trust is the Judge's 0.25, NOT the rubric value
    # (rubric would give contradicted=0.30). Proves the tier is Judge-set, not hardcoded.
    row = conn.execute("SELECT trust FROM claims WHERE claim_id='team-01'").fetchone()
    assert row["trust"] == 0.25
    assert row["trust"] != ledger.TRUST_RUBRIC["contradicted"]

    # adjudication audit trail + stored memo exist
    assert conn.execute("SELECT COUNT(*) c FROM adjudications").fetchone()["c"] >= 1
    memo = conn.execute("SELECT memo_md, decision FROM memos WHERE founder_id=?",
                        (fid,)).fetchone()
    assert memo["decision"] == "pass"
    assert memo["memo_md"].lstrip().startswith("## ⚠ Contradictions found")  # contradictions first
    assert result["violations"].ok  # all cited ids real


def test_contested_selection_matches_tiers():
    from app.memory.models import Claim
    def mk(corr):
        return Claim(id="x", axis="founder", text="t", stance="neutral", evidence="e",
                     source_url="u", source_type="web", corroboration=corr, trust=0.5)
    assert ledger.is_contested(mk("contradicted"))
    assert ledger.is_contested(mk("self_reported"))
    assert not ledger.is_contested(mk("corroborated"))
