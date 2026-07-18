"""Block 5 gate: missing data renders the brief's phrasing ('not disclosed'), NEVER a
generated value. Plus per-axis stays unblended and the latency strip records. No keys."""
import json
import re

import pytest

from app import instrument
from app.decision import decision as dec
from app.memory import db, ingest
from app.memory.models import Claim, Founder
from app.screening import thesis as th


def _claim(cid, text):
    return Claim(id=cid, axis="traction", text=text, stance="supports", evidence="e",
                 source_url="https://x.example", source_type="deck",
                 corroboration="self_reported", trust=0.4, observed_at="2026-07-18")


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_db(c)
    ingest.upsert_founder(c, Founder(id="f1", name="Test"))
    ingest.store_claim(c, "f1", _claim("trac-01", "Monthly churn is under 2 percent."))
    ingest.store_claim(c, "f1", _claim("trac-02", "ARR is 480K dollars."))
    return c


def test_missing_field_renders_phrase_never_a_value(conn):
    claims = ingest.get_claims(conn, "f1")
    report = {g["field"]: g for g in dec.gap_report(claims)}

    # Churn IS mentioned -> present, cites the claim (not a gap).
    assert report["Churn"]["status"] == "present"
    assert "trac-01" in report["Churn"]["claim_ids"]

    # Cap table is NOT mentioned anywhere -> gap, rendered as the brief's exact phrase.
    cap = report["Cap table"]
    assert cap["status"] == "gap"
    assert cap["rendered"] == "Cap table: not disclosed"       # exact phrase
    assert "value" not in cap                                   # no fabricated field

    # HARD guarantee: no gap entry contains any digit (i.e. no invented number).
    for g in dec.gap_report(claims):
        if g["status"] == "gap":
            assert not re.search(r"\d", g["rendered"])


def test_per_axis_is_unblended(conn):
    conn.execute("INSERT INTO axis_scores VALUES ('f1','founder',7.8,?,?,?,?,?)",
                 ("strong", "r", 0.24, "t", "2026-07-18"))
    conn.commit()
    axes = dec.per_axis(conn, "f1")
    assert {a["axis"] for a in axes} == {"founder", "market", "idea"}   # three, separate
    founder = next(a for a in axes if a["axis"] == "founder")
    assert founder["score"] == 7.8
    # unscored axes are honestly flagged, not invented
    assert next(a for a in axes if a["axis"] == "market")["status"] == "not yet screened"


def test_latency_strip_records_and_renders(conn):
    with instrument.stage(conn, "f1", "extract"):
        pass
    strip = instrument.latency_strip(conn, "f1")
    assert [s for s, _ in strip["stages"]] == ["extract"]
    assert strip["total_seconds"] >= 0


def test_build_and_render_brief(conn):
    conn.execute("INSERT OR REPLACE INTO memos VALUES ('f1',?,?,?,?,?,?,?)",
                 ("Pre-seed AI Infra", "pass",
                  json.dumps({"amount_usd": 100000, "claims_it_turns_on": ["trac-01"],
                              "what_would_change_our_mind": "reference checks"}),
                  "## Recommendation\nPass [trac-01 · 0.40 · self_reported].",
                  "bull", "bear", "2026-07-18"))
    conn.commit()
    thesis = th.load_thesis("config/thesis_preseed_ai_infra.yaml")
    brief = dec.build(conn, "f1", thesis)
    assert brief["decision"] == "pass"
    out = dec.render(brief)
    assert "not averaged" in out                # unblended framing
    assert "Cap table: not disclosed" in out    # gap rendered
    assert "signal→decision" in out             # latency strip present
    # no composite/blended score key leaked into the brief
    assert not ({"average", "blended", "composite", "overall"} & set(brief))
