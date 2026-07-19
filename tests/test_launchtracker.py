"""Launch Tracker adapter: newly-launched companies parsed from the public Substack RSS.

Two properties matter beyond "it parses": the LinkedIn URL in every entry must never
become an entity key (linkedin.com is on the resolve.py infrastructure blacklist, so it
would collide every founder onto one key), and the topic filter must actually exclude
non-matching entries rather than ingesting the whole feed.
"""
import pytest

from app import config
from app.memory import db
from app.sources import launchtracker

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0"><channel>
<item><title>Company Launch Tracker #81</title>
<link>https://companylaunchtracker.substack.com/p/company-launch-tracker-81</link>
<pubDate>Mon, 16 Jun 2026 18:01:05 GMT</pubDate>
<content:encoded><![CDATA[
<h2>Julaiti Alafate - Co-Founder &amp; CTO at <a href="https://skillset.co/">Skillset</a></h2>
<p><strong>FounderDNA:</strong> Technical Founder, Doctorate Degree, Former FAANG</p>
<p><strong>Prior Experience:</strong> Computer Science PhD at UC San Diego, Staff Research Scientist at Meta</p>
<p><strong>Connect on:</strong> <a href="https://www.linkedin.com/in/julaiti">LinkedIn</a></p>
<p><a href="https://skillset.co/">Skillset</a> is an AI platform for IT and product support teams.</p>
<p><strong>HQ:</strong> San Francisco, California, United States</p>
<p><strong>Industry:</strong> AI Agents, IT Support Software | <strong>Team Size:</strong> 2</p>
<p><strong>Key Investors:</strong> Gradient Ventures, First Harmonic</p>
<h2>Luba Greenwood - Chief Executive Officer at <a href="https://mwyngil.com/">Mwyngil Therapeutics</a></h2>
<p><strong>FounderDNA:</strong> Serial Founder, Prior Exit</p>
<p><strong>Connect on:</strong> <a href="https://www.linkedin.com/in/luba">LinkedIn</a></p>
<p><a href="https://mwyngil.com/">Mwyngil Therapeutics</a> is a biopharmaceutical company developing small-molecule therapies.</p>
<p><strong>HQ:</strong> Boston, Massachusetts, United States</p>
<p><strong>Industry:</strong> Biotech | <strong>Team Size:</strong> 8</p>
<p><strong>Key Investors:</strong> PureTech Health</p>
]]></content:encoded></item></channel></rss>"""


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(launchtracker, "get_text", lambda *a, **k: FEED)
    c = db.connect()
    db.init_db(c)
    return c


def test_parses_entry_fields_and_uses_domain_plus_name_as_keys(conn):
    items = launchtracker.scan(conn, "IT support", replay=True)
    assert len(items) == 1
    it = items[0]
    assert it["label"] == "Skillset"
    # domain + person name = the two co-occurring keys resolution requires.
    assert it["keys"] == {"domain": "skillset.co", "name": "Julaiti Alafate"}

    content = conn.execute("SELECT content FROM signals WHERE id=?",
                           (it["signal_id"],)).fetchone()["content"]
    for expected in ["Skillset", "founder=Julaiti Alafate", "team_size=2",
                     "hq=San Francisco", "Gradient Ventures", "Former FAANG"]:
        assert expected in content, f"missing {expected!r} in {content!r}"


def test_linkedin_is_never_an_entity_key(conn):
    for it in launchtracker.scan(conn, "a", replay=True):
        assert "linkedin" not in str(it["keys"]).lower()


def test_topic_filter_excludes_non_matching_entries(conn):
    assert [i["label"] for i in launchtracker.scan(conn, "biopharmaceutical", replay=True)] \
        == ["Mwyngil Therapeutics"]
    assert launchtracker.scan(conn, "quantum compilers", replay=True) == []


def test_rescan_dedups(conn):
    first = launchtracker.scan(conn, "IT support", replay=True)
    again = launchtracker.scan(conn, "IT support", replay=True)
    assert first[0]["inserted"] is True
    assert again[0]["inserted"] is False
    assert again[0]["signal_id"] == first[0]["signal_id"]
