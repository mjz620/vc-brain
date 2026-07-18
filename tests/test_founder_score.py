"""Block R2 gate: Founder Score is deterministic, persists (append-only history,
never resets), distinguishes low-coverage from low-score (cold-start), and feeds the
Founder axis as an input. No LLM anywhere in this module."""
import pytest

from app.memory import db, founder_score as fs, ingest
from app.memory.models import Claim, Founder, Signal
from app.screening import axes


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_db(c)
    ingest.upsert_founder(c, Founder(id="f1", name="Cold Start"))
    for url, content in [
        ("https://github.com/cs/evalkit", "cs/evalkit: eval harness | stars=1420 forks=90"),
        ("https://github.com/cs/evalkit/commits",
         "velocity: commits_6w=61 active_days=40 window_since=2026-06-06 repo=cs/evalkit"),
        ("https://news.ycombinator.com/item?id=1", "Show HN: Evalkit | points=890"),
    ]:
        sid, _ = ingest.ingest_signal(c, Signal(source="github" if "github" in url else "hn",
                                                source_url=url, content=content))
        c.execute("INSERT INTO resolutions VALUES (?,?,?,?)", (sid, "f1", "t", "now"))
    c.commit()
    return c


def _claim(cid, axis, text, corroboration="single_source"):
    return Claim(id=cid, axis=axis, text=text, stance="supports", evidence="e",
                 source_url="https://x", source_type="web",
                 corroboration=corroboration, trust=0.6)


def test_dimensions_deterministic_and_cold_start_honest(conn):
    cur = fs.compute(conn, "f1")
    d = cur["dimensions"]
    assert d["execution_velocity"] == 10.0  # 61 commits / 40 active days saturates
    assert d["community_pull"] and d["community_pull"] > 9
    assert d["integrity"] is None           # no claims yet -> unassessed, NOT zero
    assert cur["coverage"] == 0.0           # cold start: high signal, low coverage
    assert cur["score"] and cur["score"] > 9
    assert fs.compute(conn, "f1") == cur    # deterministic


def test_history_appends_never_resets(conn):
    fs.recompute(conn, "f1", "scan", now="2026-07-01T00:00:00Z")
    fs.recompute(conn, "f1", "diligence", now="2026-07-18T00:00:00Z")
    st = fs.stored(conn, "f1")
    assert [h["trigger"] for h in st["history"]] == ["scan", "diligence"]
    assert st["history"][0]["timestamp"] == "2026-07-01T00:00:00Z"  # untouched


def test_integrity_drops_on_contradicted_claims(conn):
    ingest.store_claim(conn, "f1", _claim("t-1", "founder", "exit claimed",
                                          corroboration="contradicted"))
    ingest.store_claim(conn, "f1", _claim("t-2", "market", "market sized"))
    d = fs.compute(conn, "f1")["dimensions"]
    assert d["integrity"] == 5.0  # 1 of 2 contradicted


def test_coverage_counts_record_areas(conn):
    ingest.store_claim(conn, "f1", _claim("t-1", "founder", "9 years at brokers"))
    ingest.store_claim(conn, "f1", _claim("t-2", "traction", "$480K ARR claimed"))
    cov = fs.compute(conn, "f1")["coverage"]
    # founder background + traction + revenue ("arr") = 3 of 13 areas
    assert cov == round(3 / 13, 2)


def test_founder_axis_receives_score_as_input(conn):
    fs.recompute(conn, "f1", "scan", now="2026-07-01T00:00:00Z")
    summary = axes.founder_summary(conn, "f1")
    assert "Persistent Founder Score" in summary
    assert "distinct from this screen" in summary
