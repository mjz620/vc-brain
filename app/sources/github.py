"""GitHub adapter: recently-created repos in a sector's topic, ranked by stars.

Cold-start instrument: velocity/consistency signals, not totals (spec §2.2). Each repo
becomes one Signal; entity keys are the owner handle + any linked homepage domain, so a
repo that links a personal domain can reach the >=2-key bar on its own.
"""
from ..memory import ingest
from ..memory.models import Signal
from .http import domain_of, get_json

SEARCH = "https://api.github.com/search/repositories"
# Fixed created-since window keeps the query string (and thus the cache key) stable
# across days, so replay stays deterministic.
CREATED_SINCE = "2024-01-01"


def scan(conn, topic: str, *, replay: bool, limit: int = 15) -> list[dict]:
    q = f"topic:{topic} created:>{CREATED_SINCE}"
    data = get_json(SEARCH, {"q": q, "sort": "stars", "order": "desc",
                             "per_page": limit}, replay=replay)
    items = []
    for repo in data.get("items", []):
        owner = repo["owner"]["login"]
        domain = domain_of(repo.get("homepage"))
        content = (f"{repo['full_name']}: {repo.get('description') or ''} | "
                   f"stars={repo['stargazers_count']} forks={repo['forks_count']} "
                   f"open_issues={repo['open_issues_count']} created={repo['created_at']}")
        sig = Signal(source="github", source_url=repo["html_url"], content=content,
                     observed_at=repo["created_at"])
        sid, ins = ingest.ingest_signal(conn, sig)
        items.append({"signal_id": sid, "inserted": ins, "label": repo["full_name"],
                      "keys": {"github": owner, "domain": domain}})
    return items
