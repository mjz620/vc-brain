"""Y Combinator adapter: accelerator cohorts (brief MVP 5 names "accelerator cohorts").

Public companies API, free, no auth. Each company becomes one Signal; entity keys are
the YC slug + the company website domain, so cohort companies clear the >=2-key bar and
resolve on their own.
"""
from ..memory import ingest
from ..memory.models import Signal
from .http import domain_of, get_json

API = "https://api.ycombinator.com/v0.1/companies"


def scan(conn, query: str, *, replay: bool, limit: int = 10) -> list[dict]:
    data = get_json(API, {"q": query}, replay=replay)
    items = []
    for co in data.get("companies", [])[:limit]:
        domain = domain_of(co.get("website"))
        # locations/regions come straight off the API and were previously discarded.
        # They are the only real geography this system ingests, so query.py reads
        # them back out of the content by regex rather than guessing a founder's city.
        content = (f"YC {co.get('batch')}: {co['name']} — {co.get('oneLiner') or ''} | "
                   f"team_size={co.get('teamSize')} tags={','.join(co.get('tags') or [])} "
                   f"status={co.get('status')} "
                   f"loc={'; '.join(co.get('locations') or []) or 'unknown'} "
                   f"regions={'; '.join(co.get('regions') or []) or 'unknown'}")
        sig = Signal(source="yc", source_url=co.get("url") or API, content=content)
        sid, ins = ingest.ingest_signal(conn, sig)
        items.append({"signal_id": sid, "inserted": ins, "label": co["name"],
                      "keys": {"yc": co.get("slug") or "", "domain": domain}})
    return items
