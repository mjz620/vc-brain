"""Block 3 gate (CLAUDE.md §6): three axes render separately with trends; nothing
averages them. LLM is mocked so these run with no ANTHROPIC_API_KEY."""
import pytest

from app import llm
from app.memory import db, ingest
from app.memory.models import Founder, Signal
from app.screening import axes as ax
from app.screening import firstpass, thesis as th


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_db(c)
    ingest.upsert_founder(c, Founder(id="f1", name="Test Founder",
                                     entity_keys={"github": "nferris"}))
    sid, _ = ingest.ingest_signal(c, Signal(source="github",
                                            source_url="https://github.com/nferris/x",
                                            content="repo 9 wks old, 1420 stars"))
    c.execute("INSERT INTO resolutions VALUES (?,?,?,?)", (sid, "f1", "test", "now"))
    c.commit()
    return c


def _mock_llm(monkeypatch, viable=True, score=6.5):
    def fake(tier, system, user, schema, *, replay, max_tokens=1024):
        if schema.__name__ == "FirstPass":
            return schema(viable=viable, reason="wrong sector" if not viable else "ok")
        return schema(score=score, stance="mixed", coverage=0.3,
                      rationale="per the Pre-seed AI Infra thesis, ...")
    monkeypatch.setattr(llm, "call", fake)


def test_thesis_configs_differ():
    a = th.load_thesis("config/thesis_preseed_ai_infra.yaml")
    b = th.load_thesis("config/thesis_alt.yaml")
    assert a.name != b.name
    assert a.risk_appetite == "high" and b.risk_appetite == "low"
    assert a.name in th.lens(a)  # lens references the thesis by name


def test_three_axes_render_separately_never_averaged(conn, monkeypatch):
    _mock_llm(monkeypatch)
    thesis = th.load_thesis("config/thesis_preseed_ai_infra.yaml")
    result = ax.screen(conn, "f1", thesis, replay=True)
    assert result["killed"] is False
    assert set(result["axes"]) == {"founder", "market", "idea"}  # three, separate
    # no blended/averaged/composite/overall score anywhere in the result
    assert not ({"average", "blended", "composite", "overall", "score"} & set(result))
    for a in result["axes"].values():
        assert {"score", "stance", "coverage", "rationale", "trend"} <= set(a)
        assert a["trend"] == "new"  # first score for each axis


def test_trend_computed_from_history(conn):
    for s in (6.0, 7.0):  # two founder-axis scores over time
        conn.execute("INSERT INTO axis_scores VALUES ('f1','founder',?,?,?,?,?,?)",
                     (s, "mixed", "r", 0.3, "t", f"2026-07-1{int(s)}"))
    conn.commit()
    assert ax.trend(conn, "f1", "founder") == "improving"
    conn.execute("INSERT INTO axis_scores VALUES ('f1','founder',6.9,?,?,?,?,?)",
                 ("mixed", "r", 0.3, "t", "2026-07-18"))
    conn.commit()
    assert ax.trend(conn, "f1", "founder") == "stable"  # 6.9 vs 7.0 within 0.3


def test_first_pass_kill_logs_reason_and_skips_axes(conn, monkeypatch):
    _mock_llm(monkeypatch, viable=False)
    thesis = th.load_thesis("config/thesis_alt.yaml")
    result = ax.screen(conn, "f1", thesis, replay=True)
    assert result["killed"] is True
    assert "wrong sector" in result["kill_reason"]
    row = conn.execute("SELECT reason FROM kill_log WHERE founder_id='f1'").fetchone()
    assert row is not None  # kill reason logged
    # no axis scores written when killed
    assert conn.execute("SELECT COUNT(*) c FROM axis_scores").fetchone()["c"] == 0


def test_prompt_loading():
    from app.promptlib import load_prompt
    # filled prompt files take over from the embedded default...
    out = load_prompt("rubric_founder", "EMBEDDED_DEFAULT")
    assert out != "EMBEDDED_DEFAULT" and "FOUNDER axis" in out
    # ...and a missing/unfilled prompt still falls back
    assert load_prompt("no_such_prompt", "EMBEDDED_DEFAULT") == "EMBEDDED_DEFAULT"
