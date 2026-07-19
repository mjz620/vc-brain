"""Company Launch Tracker adapter: newly-launched companies with founder background.

Public Substack RSS, free, no auth. This is the earliest-signal channel in the stack —
entries appear at launch, typically before a company has GitHub traction, Product Hunt
presence, or a funding announcement, which is exactly the pre-fundraising window the
sourcing brief cares about.

Read via the feed's own machine-readable interface rather than scraping the site HTML.
The feed carries a truncated preview per issue, but each preview still contains the
issue's company entries, so no page fetching is needed.

Entity keys are the company domain + the founder name. The entries also carry a
LinkedIn URL; it is deliberately NOT used as an identity key — linkedin.com is on the
infrastructure blacklist in memory/resolve.py, and using it would let every founder
collide on one key.
"""
import html
import re
import xml.etree.ElementTree as ET

from ..memory import ingest
from ..memory.models import Signal
from .http import domain_of, get_text

FEED = "https://companylaunchtracker.substack.com/feed"
_CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"

# <h2>Name - Role at <a href="url">Company</a></h2> opens each company entry.
_ENTRY = re.compile(
    r"<h2>(?P<person>[^<]+?)\s+-\s+(?P<role>[^<]+?)\s+at\s+"
    r"<a href=\"(?P<url>[^\"]+)\"[^>]*>(?P<company>[^<]+)</a>\s*</h2>(?P<body>.*?)"
    r"(?=<h2>|$)", re.S)
_TAG = re.compile(r"<[^>]+>")


def _field(body: str, label: str) -> str:
    m = re.search(rf"<strong>{label}:</strong>(.*?)</p>", body, re.S)
    return _text(m.group(1)) if m else ""


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", _TAG.sub(" ", fragment))).strip(" |")


def scan(conn, query: str, *, replay: bool, limit: int = 10) -> list[dict]:
    xml = get_text(FEED, {}, replay=replay)
    root = ET.fromstring(xml)
    items = []
    for issue in root.findall("channel/item"):
        raw = (issue.find(_CONTENT).text or "") if issue.find(_CONTENT) is not None else ""
        issue_url = issue.findtext("link") or FEED
        for m in _ENTRY.finditer(raw):
            person, company = m["person"].strip(), html.unescape(m["company"]).strip()
            body = m["body"]
            # The company description sits in the one <p> that is not a labelled field.
            desc = ""
            for p in re.findall(r"<p>(.*?)</p>", body, re.S):
                if "<strong>" not in p:
                    desc = _text(p)
                    break
            dna = _field(body, "FounderDNA")
            prior = _field(body, "Prior Experience")
            hq = _field(body, "HQ")
            investors = _field(body, "Key Investors")
            industry = _field(body, "Industry")
            team = ""
            if industry:
                # "Industry: X | Team Size: N" share one <p>.
                parts = re.split(r"Team Size:", industry)
                industry = parts[0].strip(" |")
                team = parts[1].strip() if len(parts) > 1 else ""

            blob = f"{company} {desc} {industry} {dna} {prior}"
            if query.lower() not in blob.lower():
                continue
            content = (f"Launch Tracker: {company} — {desc} | founder={person} "
                       f"({m['role'].strip()}) founder_dna={dna} prior={prior} "
                       f"industry={industry} team_size={team} hq={hq} "
                       f"investors={investors}")
            sig = Signal(source="launchtracker", source_url=issue_url, content=content,
                         observed_at=issue.findtext("pubDate"))
            sid, ins = ingest.ingest_signal(conn, sig)
            items.append({"signal_id": sid, "inserted": ins, "label": company,
                          "keys": {"domain": domain_of(m["url"]), "name": person}})
            if len(items) >= limit:
                return items
    return items
