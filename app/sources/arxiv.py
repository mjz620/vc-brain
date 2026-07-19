"""arXiv adapter: recent papers in a sector (free Atom API).

The "paper worth a phone call" case (spec §2.2): a paper that links a repo gets a
GitHub handle as a second entity key, so it can resolve to a founder; papers with only
an author name stay in the pool and are drop-logged.
"""
import re
import xml.etree.ElementTree as ET

from ..memory import ingest
from ..memory.models import Signal
from .http import get_text

API = "http://export.arxiv.org/api/query"
_NS = {"a": "http://www.w3.org/2005/Atom",
       "ax": "http://arxiv.org/schemas/atom"}
_GH = re.compile(r"github\.com/([A-Za-z0-9_-]+)")


def scan(conn, query: str, *, replay: bool, limit: int = 10) -> list[dict]:
    xml = get_text(API, {"search_query": f"all:{query}", "start": 0,
                         "max_results": limit, "sortBy": "submittedDate",
                         "sortOrder": "descending"}, replay=replay)
    root = ET.fromstring(xml)
    items = []
    for entry in root.findall("a:entry", _NS):
        title = (entry.findtext("a:title", "", _NS) or "").strip().replace("\n", " ")
        url = entry.findtext("a:id", "", _NS)
        summary = entry.findtext("a:summary", "", _NS) or ""
        authors = [a.findtext("a:name", "", _NS)
                   for a in entry.findall("a:author", _NS)]
        first = authors[0] if authors else ""
        # Repo links usually live in the arxiv:comment field ("Code is available
        # at https://github.com/..."), not the abstract — scan title+comment too.
        comment = entry.findtext("ax:comment", "", _NS) or ""
        gh = _GH.search(f"{summary} {comment} {title}")
        content = f"arXiv: {title} | authors={', '.join(authors)}"
        sig = Signal(source="arxiv", source_url=url, content=content,
                     observed_at=entry.findtext("a:published", None, _NS))
        sid, ins = ingest.ingest_signal(conn, sig)
        keys = {"arxiv": first.lower().replace(" ", "-")}
        if gh:
            keys["github"] = gh.group(1)
        items.append({"signal_id": sid, "inserted": ins, "label": title, "keys": keys})
    return items
