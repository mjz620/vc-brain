"""Open-web discovery adapter, powered by the Tavily search API.

The other five adapters each scan one curated surface. This one is unbounded: it
searches the open web for companies matching a thesis topic, which is the only way
to reach founders who are not on GitHub, not in a cohort, and not on a launch list.

Two deliberate constraints, because unbounded breadth is also unbounded noise:

1. Ingested as source="websearch", NOT "tavily". The tavily source label already
   carries diligence enrichment pages, which are attached directly to a founder and
   never entity-resolved (44 signals, 0 resolutions). Mixing discovery into that
   label would make the channel-yield table meaningless for both.

2. A result only becomes a candidate if its domain looks like a COMPANY's own site.
   Search results are mostly media, directories and listicles; their domains are on
   the aggregator blacklist in memory/resolve.py, so they can never act as an
   identity key. Without that guard every company named in one TechCrunch article
   would share techcrunch.com as a key and falsely merge.

Precision here is lower than the curated adapters by construction. Results that
cannot produce two keys land in the drop log, which is the honest outcome.
"""
import re

from ..memory import ingest
from ..memory.models import Signal
from ..memory.resolve import is_infra_domain
from . import tavily
from .http import domain_of

# Trailing site-name furniture in result titles: "Acme — AI for X | TechCrunch".
_TITLE_TAIL = re.compile(r"\s*[|·—–-]\s*[^|·—–-]{0,40}$")


def _company_from(title: str, domain: str) -> str:
    """The company name as an entity key. Prefer the leading token of the title;
    fall back to the registrable part of its own domain."""
    head = _TITLE_TAIL.sub("", (title or "").strip()).strip()
    head = re.split(r"\s+[-–—:|]\s+", head)[0].strip()
    if 2 <= len(head) <= 60:
        return head
    return domain.split(".")[0] if domain else ""


def scan(conn, query: str, *, replay: bool, limit: int = 10) -> list[dict]:
    resp = tavily.web_search(f"{query} startup company founded by", replay=replay,
                             max_results=max(limit, 6))
    items = []
    for r in resp.get("results", []):
        url = r.get("url")
        if not url:
            continue
        domain = domain_of(url)
        # A media/aggregator domain is not an identity. Skip rather than ingest a
        # signal that can only ever drop — the drop log should record real
        # ambiguity, not our own known-bad candidates.
        if not domain or is_infra_domain(domain):
            continue
        title = (r.get("title") or "").strip()
        name = _company_from(title, domain)
        if not name:
            continue
        content = (f"Web discovery: {title} — {(r.get('content') or '')[:600]} "
                   f"| domain={domain} query={query}")
        sid, ins = ingest.ingest_signal(conn, Signal(
            source="websearch", source_url=url, content=content,
            observed_at=r.get("published_date")))
        items.append({"signal_id": sid, "inserted": ins, "label": name,
                      "keys": {"domain": domain, "name": name}})
        if len(items) >= limit:
            break
    return items
