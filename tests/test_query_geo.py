"""Geography and headcount are mechanically evaluable from real ingested YC fields
(app/sources/yc.py writes loc=/regions=/team_size= into signal content).

The gate that matters: a founder carrying none of that data is EXCLUDED and counted
as uncovered — never assumed to match, and never silently passed through. An empty
result set with disclosed coverage is a real answer; it is not "criterion ignored".
"""
import pytest

from app import config, llm, query
from app.memory import db, ingest
from app.memory.models import Founder, Signal

YC = ("YC W24: Cadence — workflow infra | team_size=6 tags=Infrastructure "
      "status=Active loc=Berlin, Germany regions=Europe")
YC_BIG = ("YC S23: Groundwork — data infra | team_size=48 tags=Infrastructure "
          "status=Active loc=San Francisco regions=United States of America")
BARE = "llm eval harness for agents | stars=1420"  # github: no geo, no headcount


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    c = db.connect()
    db.init_db(c)
    for fid, name, source, url, content in [
        ("f-berlin", "Cadence", "yc", "https://ycombinator.com/companies/cadence", YC),
        ("f-sf", "Groundwork", "yc", "https://ycombinator.com/companies/gw", YC_BIG),
        ("f-bare", "Unknown Co", "github", "https://github.com/nf/x", BARE),
    ]:
        ingest.upsert_founder(c, Founder(id=fid, name=name))
        sid, _ = ingest.ingest_signal(c, Signal(
            source=source, source_url=url, content=content))
        c.execute("INSERT INTO resolutions VALUES (?,?,?,?)", (sid, fid, "t", "now"))
    c.commit()
    return c


def _parse_as(monkeypatch, criteria):
    def fake(tier, system, user, schema, *, replay, max_tokens=1024):
        return schema(criteria=criteria)
    monkeypatch.setattr(llm, "call", fake)


def test_location_matches_and_uncovered_founders_are_excluded(conn, monkeypatch):
    _parse_as(monkeypatch, [
        {"text": "in Berlin", "kind": "location", "value": "berlin"}])
    out = query.run(conn, "founders in Berlin", replay=True)

    assert [r["id"] for r in out["results"]] == ["f-berlin"]
    # f-bare has no geography at all: dropped, and NOT counted as evaluated.
    cov = out["coverage"][0]
    assert cov["criterion"] == "berlin"
    assert cov["evaluated_founders"] == 2   # the two yc founders carry loc=
    assert cov["candidate_founders"] == 3   # f-bare was considered but uncoverable


def test_region_satisfies_location_and_empty_result_is_still_evaluated(conn, monkeypatch):
    _parse_as(monkeypatch, [
        {"text": "European", "kind": "location", "value": "europe"}])
    assert [r["id"] for r in query.run(conn, "European founders", replay=True)["results"]] \
        == ["f-berlin"]

    _parse_as(monkeypatch, [
        {"text": "in Tokyo", "kind": "location", "value": "tokyo"}])
    out = query.run(conn, "founders in Tokyo", replay=True)
    # Zero matches, but the criterion WAS applied over 2 founders — the distinction
    # between "no one matched" and "we could not check" is the whole point.
    assert out["results"] == []
    assert out["coverage"][0]["evaluated_founders"] == 2
    assert out["ignored_criteria"] == []


def test_team_size_comparators(conn, monkeypatch):
    for spec, expected in [("<10", ["f-berlin"]), (">40", ["f-sf"]), ("6", ["f-berlin"])]:
        _parse_as(monkeypatch, [
            {"text": "small team", "kind": "team_size", "value": spec}])
        got = [r["id"] for r in query.run(conn, "small team", replay=True)["results"]]
        assert got == expected, f"team_size {spec} returned {got}"


def test_compound_query_mixes_evaluable_and_honestly_ignored(conn, monkeypatch):
    _parse_as(monkeypatch, [
        {"text": "Berlin", "kind": "location", "value": "berlin"},
        {"text": "top-tier accelerator", "kind": "source", "value": "yc"},
        {"text": "small team", "kind": "team_size", "value": "<10"},
        {"text": "no prior VC backing", "kind": "not_evaluable",
         "value": "no funding-history source ingested"},
    ])
    out = query.run(conn, "Berlin, top accelerator, small team, no prior VC backing",
                    replay=True)
    assert [r["id"] for r in out["results"]] == ["f-berlin"]
    # Funding stays honestly unevaluated — there is genuinely no such data ingested.
    assert out["ignored_criteria"][0]["text"] == "no prior VC backing"
    assert {c["criterion"] for c in out["coverage"]} == {"berlin", "<10"}
