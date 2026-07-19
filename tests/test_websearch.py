"""Open-web discovery adapter.

The property that matters is the guard, not the parsing: search results are mostly
media and directories, and if their domains became identity keys then every company
named in one article would share a key and falsely merge. Those domains are on the
INFRA_DOMAINS blacklist, and this adapter skips them before ingest.
"""
import pytest

from app import config
from app.memory import db
from app.sources import websearch

RESULTS = {"results": [
    {"url": "https://acme-robotics.com/about", "title": "Acme Robotics — warehouse AI",
     "content": "Acme Robotics builds autonomous picking.", "published_date": None},
    {"url": "https://techcrunch.com/2026/01/05/five-ai-startups",
     "title": "Five AI startups to watch | TechCrunch",
     "content": "Acme, Beta, Gamma, Delta and Epsilon all raised seed rounds."},
    {"url": "https://www.crunchbase.com/organization/beta-labs",
     "title": "Beta Labs - Crunchbase Company Profile", "content": "Beta Labs profile."},
    {"url": "https://github.com/someone/repo", "title": "someone/repo", "content": "code"},
    {"url": "https://betalabs.ai", "title": "Beta Labs | Inference infrastructure",
     "content": "Beta Labs runs inference."},
]}


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(websearch.tavily, "web_search",
                        lambda q, *, replay, max_results=6: RESULTS)
    c = db.connect()
    db.init_db(c)
    return c


def test_media_and_directory_domains_never_become_candidates(conn):
    items = websearch.scan(conn, "inference", replay=True)
    domains = {i["keys"]["domain"] for i in items}
    assert domains == {"acme-robotics.com", "betalabs.ai"}
    # The three that would poison resolution are gone entirely.
    for bad in ("techcrunch.com", "crunchbase.com", "github.com"):
        assert bad not in domains


def test_company_name_is_stripped_of_site_furniture(conn):
    by_domain = {i["keys"]["domain"]: i for i in websearch.scan(conn, "x", replay=True)}
    assert by_domain["acme-robotics.com"]["keys"]["name"] == "Acme Robotics"
    assert by_domain["betalabs.ai"]["keys"]["name"] == "Beta Labs"


def test_ingests_under_its_own_source_not_tavily(conn):
    items = websearch.scan(conn, "inference", replay=True)
    sources = {r["source"] for r in
               conn.execute("SELECT DISTINCT source FROM signals").fetchall()}
    # "tavily" is the diligence-enrichment label; discovery must not blend into it
    # or the channel-yield table becomes meaningless for both.
    assert sources == {"websearch"}
    assert all(i["keys"]["domain"] and i["keys"]["name"] for i in items)


def test_rescan_dedups(conn):
    first = websearch.scan(conn, "inference", replay=True)
    again = websearch.scan(conn, "inference", replay=True)
    assert first[0]["inserted"] is True
    assert again[0]["inserted"] is False


def test_subdomains_of_blacklisted_platforms_are_infra():
    """Exact matching let every subdomain through — a GitHub Pages site or a
    Substack newsletter would have acted as a linking identity key."""
    from app.memory.resolve import is_infra_domain
    for d in ("substack.com", "eastwind.substack.com", "username.github.io",
              "someone.medium.com", "foo.notion.site", "crv.com", "siliconangle.com"):
        assert is_infra_domain(d), d
    for d in ("acme-robotics.com", "betalabs.ai", "skillset.co", "notsubstack.com"):
        assert not is_infra_domain(d), d
