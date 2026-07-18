"""Block R4 gate: NL query parses -> mechanical filter (non-evaluable flagged, never
guessed); trace endpoint returns the full evidence chain; apply intake takes deck+name
only. LLM mocked; server exercised against a temp DB."""
import pytest

from app import config, llm, query
from app.memory import db, ingest
from app.memory.models import Claim, Founder, Signal


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    c = db.connect()
    db.init_db(c)
    ingest.upsert_founder(c, Founder(id="f1", name="Eval Founder"))
    sid, _ = ingest.ingest_signal(c, Signal(
        source="github", source_url="https://github.com/nf/x",
        content="llm eval harness for agents | stars=1420"))
    c.execute("INSERT INTO resolutions VALUES (?,?,?,?)", (sid, "f1", "t", "now"))
    c.commit()
    return c


def test_nl_query_filters_and_flags(conn, monkeypatch):
    def fake(tier, system, user, schema, *, replay, max_tokens=1024):
        return schema(criteria=[
            {"text": "AI infra", "kind": "keyword", "value": "llm"},
            {"text": "technical founder", "kind": "source", "value": "github"},
            {"text": "no prior VC backing", "kind": "not_evaluable",
             "value": "no funding-history source ingested"},
        ])
    monkeypatch.setattr(llm, "call", fake)
    out = query.run(conn, "technical founder, AI infra, no prior VC backing",
                    replay=True)
    assert [r["id"] for r in out["results"]] == ["f1"]
    assert out["results"][0]["matched_keywords"] == ["llm"]
    assert out["ignored_criteria"][0]["text"] == "no prior VC backing"  # flagged, not guessed


def test_trace_endpoint_returns_chain(conn):
    ingest.store_claim(conn, "f1", Claim(
        id="team-01", axis="founder", text="ships fast", stance="supports",
        evidence="61-day streak", source_url="https://github.com/nf/x",
        source_type="github", corroboration="corroborated", trust=0.85),
        signal_ids=[])
    conn.execute("INSERT INTO adjudications VALUES (?,?,?,?,?,?,?,?)",
                 ("f1", "team-01", "pros text", "def text", "corroborated",
                  0.85, "streak verified", "now"))
    conn.commit()
    from fastapi.testclient import TestClient
    from app.server import app
    r = TestClient(app).get("/api/trace/f1/team-01").json()
    assert r["claim"]["id"] == "team-01"
    assert r["signals"][0]["source_url"] == "https://github.com/nf/x"  # via URL match
    assert r["adjudication"]["prosecution"] == "pros text"
    assert TestClient(app).get("/api/trace/f1/fake-99").status_code == 404


def test_apply_minimum_bar_deck_plus_name(conn, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    from fastapi.testclient import TestClient
    from app.server import app
    client = TestClient(app)
    r = client.post("/api/apply", json={"company": "TestCo",
                                        "deck_text": "We do X. ARR $1."}).json()
    assert r["founder_id"] == "founder-testco" and r["screened"] is False
    dup = client.post("/api/apply", json={"company": "TestCo",
                                          "deck_text": "We do X. ARR $1."}).json()
    assert dup["duplicate"] is True  # dedup holds on the apply path too
    assert client.post("/api/apply", json={"company": " ", "deck_text": ""}).status_code == 422
