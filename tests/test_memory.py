"""Block 1 acceptance gate (CLAUDE.md §6):
- claims table stores a negative-result claim with the search URL as source
- signals table is append-only
- dedup hash rejects a duplicate
"""
import sqlite3

import pytest

from app.memory import db, ingest
from app.memory.models import Claim, Founder, ScoreEntry, Signal


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_db(c)
    ingest.upsert_founder(c, Founder(id="f1", name="Test Founder"))
    return c


def test_dedup_rejects_duplicate(conn):
    sig = Signal(source="github", source_url="https://github.com/x/y",
                 content="repo created 2026-05-14")
    id1, ins1 = ingest.ingest_signal(conn, sig)
    id2, ins2 = ingest.ingest_signal(conn, sig)
    assert ins1 is True and ins2 is False
    assert id1 == id2
    assert conn.execute("SELECT COUNT(*) c FROM signals").fetchone()["c"] == 1


def test_dedup_normalizes_whitespace_and_case(conn):
    a = Signal(source="hn", source_url="https://news.ycombinator.com/item?id=1",
               content="Show HN: Tracewell")
    b = Signal(source="hn", source_url="https://news.ycombinator.com/item?id=1",
               content="  show hn:   tracewell ")
    _, ins_a = ingest.ingest_signal(conn, a)
    _, ins_b = ingest.ingest_signal(conn, b)
    assert ins_a is True and ins_b is False  # same after normalization


def test_signals_are_append_only(conn):
    sig = Signal(source="deck", source_url="deck.txt", content="ARR $480K claimed")
    sid, _ = ingest.ingest_signal(conn, sig)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM signals WHERE id = ?", (sid,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE signals SET content = 'tampered' WHERE id = ?", (sid,))


def test_negative_result_is_a_first_class_claim(conn):
    url = "https://efts.sec.gov/LATEST/search-index?q=%22DataLoom%22&forms=D"
    claim = Claim(id="dd-02", axis="founder", stance="contradicts",
                  text="No Form D exists for DataLoom's claimed $4M seed.",
                  evidence="EDGAR full-text search: no filing found.",
                  evidence_url=url, source_type="web", corroboration="corroborated",
                  trust=0.9, observed_at="2026-07-18")
    ingest.store_claim(conn, "f1", claim, signal_ids=[])
    got = ingest.get_claims(conn, "f1")
    assert len(got) == 1
    assert got[0].id == "dd-02"
    assert got[0].stance == "contradicts"
    assert got[0].evidence_url == url  # the search URL is the source


def test_score_history_is_append_only_trend(conn):
    ingest.append_score(conn, "f1", ScoreEntry(timestamp="2026-07-10", score=7.1,
                        trigger="initial"), coverage=0.22)
    ingest.append_score(conn, "f1", ScoreEntry(timestamp="2026-07-17", score=7.8,
                        trigger="rerun"), coverage=0.24)
    import json
    row = conn.execute("SELECT founder_score FROM founders WHERE id='f1'").fetchone()
    score = json.loads(row["founder_score"])
    assert [h["score"] for h in score["history"]] == [7.1, 7.8]  # appended, not overwritten
    assert score["coverage"] == 0.24
