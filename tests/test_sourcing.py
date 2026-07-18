"""Block R1 gate: thesis drives the scan queries; Activate cites the real triggering
signal (mechanically enforced); channel stats reflect the funnel. LLM + HTTP mocked."""
import pytest

from app import activate, llm
from app.memory import db, ingest
from app.memory.models import Founder, Signal
from app.screening import thesis as th
from app.sources import scanner


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_db(c)
    return c


def test_thesis_topics_drive_scan(conn, monkeypatch):
    seen: dict[str, list[str]] = {}

    def fake_adapter(name):
        def scan(conn, topic, *, replay, limit=8):
            seen.setdefault(name, []).append(topic)
            return []
        return scan

    monkeypatch.setattr(scanner, "ADAPTERS",
                        [(n, fake_adapter(n)) for n in ("github", "hn")])
    thesis = th.load_thesis("config/thesis_preseed_ai_infra.yaml")
    topics = scanner.topics_for(thesis)
    assert topics == thesis.topics and len(topics) > 1
    scanner.run_scan(conn, topics, replay=True)
    assert seen["github"] == topics  # every thesis topic scanned on every source
    assert seen["hn"] == topics
    # explicit override wins
    assert scanner.topics_for(thesis, "grpc") == ["grpc"]


def test_adapter_error_does_not_sink_scan(conn, monkeypatch):
    def ok(conn, topic, *, replay, limit=8):
        return []

    def boom(conn, topic, *, replay, limit=8):
        raise RuntimeError("rate limited")

    monkeypatch.setattr(scanner, "ADAPTERS", [("github", ok), ("hn", boom)])
    result = scanner.run_scan(conn, ["llm"], replay=True)
    assert result["counts"]["github"] == 0
    assert "rate limited" in result["counts"]["hn"]


def _seed_founder(conn):
    ingest.upsert_founder(conn, Founder(id="f1", name="Test Founder"))
    sid, _ = ingest.ingest_signal(conn, Signal(
        source="github", source_url="https://github.com/nf/x",
        content="repo: eval harness, 1420 stars", observed_at="2026-07-01"))
    conn.execute("INSERT INTO resolutions VALUES (?,?,?,?)", (sid, "f1", "test", "now"))
    conn.commit()
    return sid


def test_activate_cites_triggering_signal(conn, monkeypatch):
    sid = _seed_founder(conn)

    def fake(tier, system, user, schema, *, replay, max_tokens=1024):
        assert "1420 stars" in user  # draft sees only the real signal
        return schema(subject="Your eval harness", body="Saw your repo (1420 stars).",
                      cited_signal_url="https://github.com/nf/x")

    monkeypatch.setattr(llm, "call", fake)
    d = activate.draft(conn, "f1", "Pre-seed AI Infra", replay=True)
    row = conn.execute("SELECT * FROM outreach WHERE founder_id='f1'").fetchone()
    assert row["signal_id"] == sid and d.subject == row["subject"]


def test_activate_rejects_fabricated_citation(conn, monkeypatch):
    _seed_founder(conn)

    def fake(tier, system, user, schema, *, replay, max_tokens=1024):
        return schema(subject="s", body="b",
                      cited_signal_url="https://example.com/made-up")

    monkeypatch.setattr(llm, "call", fake)
    with pytest.raises(ValueError, match="rejected"):
        activate.draft(conn, "f1", "Pre-seed AI Infra", replay=True)
    assert conn.execute("SELECT COUNT(*) c FROM outreach").fetchone()["c"] == 0


def test_newly_resolved_founders(conn):
    sid = _seed_founder(conn)
    assert scanner.newly_resolved_founders(conn, [sid]) == [("f1", 1)]
    assert scanner.newly_resolved_founders(conn, []) == []
