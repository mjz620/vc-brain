"""ProductHunt adapter: today's launches (brief MVP 5 names "launches").

Public Atom feed, free, no auth. The feed is not query-addressable, so one cached
fetch is filtered per topic keyword client-side. Entity keys are the PH product slug +
the maker name; thinner than GitHub's, so more of these land in the drop-log — which is
the honest outcome, not a failure.
"""
import re
import xml.etree.ElementTree as ET

from ..memory import ingest
from ..memory.models import Signal
from .http import get_text

FEED = "https://www.producthunt.com/feed"
_NS = {"a": "http://www.w3.org/2005/Atom"}
_TAG = re.compile(r"<[^>]+>")


def scan(conn, query: str, *, replay: bool, limit: int = 10) -> list[dict]:
    xml = get_text(FEED, {}, replay=replay)
    root = ET.fromstring(xml)
    items = []
    for entry in root.findall("a:entry", _NS):
        title = (entry.findtext("a:title", "", _NS) or "").strip()
        link = next((l.get("href") for l in entry.findall("a:link", _NS)
                     if l.get("rel") == "alternate"), "")
        tagline = _TAG.sub(" ", entry.findtext("a:content", "", _NS) or "")
        tagline = re.sub(r"\s+", " ", tagline).split("Discussion")[0].strip()
        if query.lower() not in f"{title} {tagline}".lower():
            continue
        author = entry.findtext("a:author/a:name", "", _NS) or ""
        slug = link.rstrip("/").rsplit("/", 1)[-1] if link else ""
        content = f"ProductHunt launch: {title} — {tagline} | maker={author}"
        sig = Signal(source="producthunt", source_url=link or FEED, content=content,
                     observed_at=entry.findtext("a:published", None, _NS))
        sid, ins = ingest.ingest_signal(conn, sig)
        items.append({"signal_id": sid, "inserted": ins, "label": title,
                      "keys": {"producthunt": slug, "name": author}})
        if len(items) >= limit:
            break
    return items
