"""Hacker News adapter: Show HN posts in a sector (Algolia API, free, no auth).

Each Show HN becomes one Signal; entity keys are the HN author + the submitted URL's
domain. A domain shared with a GitHub repo links the two into one founder in resolution.
"""
from ..memory import ingest
from ..memory.models import Signal
from .http import domain_of, get_json

SEARCH = "https://hn.algolia.com/api/v1/search"


def scan(conn, query: str, *, replay: bool, limit: int = 15) -> list[dict]:
    data = get_json(SEARCH, {"query": query, "tags": "show_hn",
                             "hitsPerPage": limit}, replay=replay)
    items = []
    for hit in data.get("hits", []):
        author = hit.get("author") or ""
        domain = domain_of(hit.get("url"))
        content = (f"Show HN: {hit.get('title')} | author={author} "
                   f"points={hit.get('points')} comments={hit.get('num_comments')}")
        source_url = f"https://news.ycombinator.com/item?id={hit['objectID']}"
        sig = Signal(source="hn", source_url=source_url, content=content,
                     observed_at=hit.get("created_at"))
        sid, _ = ingest.ingest_signal(conn, sig)
        items.append({"signal_id": sid, "label": hit.get("title") or "",
                      "keys": {"hn": author, "domain": domain}})
    return items
