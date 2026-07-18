"""Entity resolution (spec §2.1).

A signal attaches to a founder only on co-occurrence of >=2 entity keys (handle+domain,
name+company, ...). Signals with fewer than 2 keys, or whose keys point at more than one
existing founder (ambiguous same-name collisions), stay in the pool and are drop-logged
— never dropped silently.
"""
import json
import re
from datetime import datetime, timezone

from .ingest import upsert_founder
from .models import Founder

# Priority order for choosing a founder's primary key / id.
_PRIORITY = ["github", "hn", "arxiv", "domain", "name"]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve(conn, items: list[dict]) -> dict:
    """Resolve a batch of {signal_id, keys, label} items.

    Returns {"resolved": n, "dropped": [(signal_id, reason)], "founders": total}.
    """
    # Seed the key index from founders already in Memory (idempotent re-scans).
    key_index: dict[tuple[str, str], str] = {}
    founders: dict[str, dict] = {}
    for f in conn.execute("SELECT id, name, entity_keys FROM founders").fetchall():
        keys = json.loads(f["entity_keys"] or "{}")
        founders[f["id"]] = {"name": f["name"], "keys": dict(keys)}
        for t, v in keys.items():
            if v:
                key_index[(t, v)] = f["id"]

    resolutions: list[tuple[str, str, str]] = []
    dropped: list[tuple[str, str]] = []

    for it in items:
        present = {t: v for t, v in it["keys"].items() if v}
        if len(present) < 2:
            dropped.append((it["signal_id"], "insufficient_entity_keys"))
            _droplog(conn, it["signal_id"], "insufficient_entity_keys", present)
            continue
        matched = {key_index[(t, v)] for t, v in present.items() if (t, v) in key_index}
        if len(matched) > 1:
            dropped.append((it["signal_id"], "ambiguous_multi_founder_match"))
            _droplog(conn, it["signal_id"], "ambiguous_multi_founder_match", present)
            continue
        if matched:
            fid = next(iter(matched))
        else:
            primary = next(present[k] for k in _PRIORITY if k in present)
            fid = "founder-" + _slug(primary)
        f = founders.setdefault(fid, {"name": None, "keys": {}})
        f["keys"].update(present)
        f["name"] = f["name"] or next(present[k] for k in _PRIORITY if k in present)
        for t, v in present.items():
            key_index[(t, v)] = fid
        resolutions.append((it["signal_id"], fid, "entity_key_cooccurrence"))

    # Upsert founders first (FK), then record resolution links.
    for fid, f in founders.items():
        upsert_founder(conn, Founder(id=fid, name=f["name"] or fid,
                                     entity_keys=f["keys"]))
    for sid, fid, method in resolutions:
        conn.execute("INSERT OR REPLACE INTO resolutions (signal_id, founder_id, "
                     "method, resolved_at) VALUES (?,?,?,?)", (sid, fid, method, _now()))
    conn.commit()

    total = conn.execute("SELECT COUNT(*) c FROM founders").fetchone()["c"]
    return {"resolved": len(resolutions), "dropped": dropped, "founders": total}


def _droplog(conn, signal_id: str, reason: str, keys: dict) -> None:
    conn.execute("INSERT INTO droplog (signal_id, reason, entity_keys, logged_at) "
                 "VALUES (?,?,?,?)", (signal_id, reason, json.dumps(keys), _now()))
    conn.commit()
