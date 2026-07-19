"""Entity resolution (spec §2.1).

A signal attaches to a founder only on co-occurrence of >=2 entity keys (handle+domain,
name+company, ...). Signals with fewer than 2 keys, or whose keys point at more than one
existing founder (ambiguous same-name collisions), stay in the pool and are drop-logged
— never dropped silently.

Infrastructure domains (github.com, youtube.com, ...) identify a platform, not a
person, so a domain key on the INFRA_DOMAINS blacklist never counts toward the
>=2-key bar and never matches/merges founders. Simplest honest behavior: such a
domain is discarded from the key set outright — it is not stored as a founder
attribute either, because a platform domain asserts nothing about identity and
storing it invites the exact false merge it caused (founder-armanified). The
original keys, infra domain included, are preserved verbatim in the drop-log row.
"""
import json
import re
from datetime import datetime, timezone

from .ingest import upsert_founder
from .models import Founder

# Priority order for choosing a founder's primary key / id.
_PRIORITY = ["github", "hn", "arxiv", "domain", "name"]

# Platform/infrastructure domains that must never act as a linking entity key.
# Exact match against the normalized netloc (www. already stripped by domain_of).
INFRA_DOMAINS = frozenset({
    "github.com", "gist.github.com", "github.io", "gitlab.com", "bitbucket.org",
    "sourceforge.net", "twitter.com", "x.com", "linkedin.com", "facebook.com",
    "instagram.com", "tiktok.com", "threads.net", "mastodon.social", "reddit.com",
    "medium.com", "substack.com", "dev.to", "youtube.com", "youtu.be", "twitch.tv",
    "notion.site", "notion.so", "docs.google.com", "drive.google.com",
    "sites.google.com", "forms.gle", "colab.research.google.com", "play.google.com",
    "chrome.google.com", "chromewebstore.google.com", "apps.apple.com",
    "addons.mozilla.org", "bit.ly", "t.co", "t.me", "telegram.me", "discord.gg",
    "discord.com", "producthunt.com", "news.ycombinator.com", "huggingface.co",
    "kaggle.com", "arxiv.org", "pypi.org", "npmjs.com",
    # Media, directories and data aggregators. Open-web discovery (sources/websearch)
    # surfaces these constantly, and one article naming five startups would otherwise
    # hand all five the same identity key and merge them.
    "techcrunch.com", "venturebeat.com", "forbes.com", "businessinsider.com",
    "bloomberg.com", "reuters.com", "wsj.com", "ft.com", "cnbc.com", "wired.com",
    "theverge.com", "axios.com", "fortune.com", "inc.com", "fastcompany.com",
    "sifted.eu", "eu-startups.com", "tech.eu", "geekwire.com", "prnewswire.com",
    "businesswire.com", "globenewswire.com",
    "crunchbase.com", "pitchbook.com", "cbinsights.com", "tracxn.com", "dealroom.co",
    "owler.com", "zoominfo.com", "glassdoor.com", "indeed.com", "wellfound.com",
    "angel.co", "g2.com", "capterra.com", "trustpilot.com", "clutch.co",
    "wikipedia.org", "quora.com", "stackoverflow.com", "ycombinator.com",
    "siliconangle.com", "techmeme.com", "hackernoon.com", "towardsdatascience.com",
    "analyticsindiamag.com", "theinformation.com", "protocol.com", "ventureradar.com",
    "startupranking.com", "producthunt.com", "betalist.com", "f6s.com",
    # VC firm sites. A "who is building X" search surfaces portfolio and thesis pages
    # constantly, and a fund is not a founder — its domain must never link one.
    "a16z.com", "sequoiacap.com", "greylock.com", "accel.com", "benchmark.com",
    "indexventures.com", "lightspeedvp.com", "crv.com", "nea.com", "bvp.com",
    "firstround.com", "initialized.com", "gradient.com", "khoslaventures.com",
    "founderscollective.com", "unusual.vc", "amplifypartners.com", "bain.com",
})


def is_infra_domain(domain: str) -> bool:
    """A blacklisted domain OR any subdomain of one.

    Exact matching alone let every subdomain through: `username.github.io`,
    `someone.substack.com` and `x.medium.com` are just as much shared infrastructure
    as their parents, and each would have acted as a linking identity key — merging
    unrelated founders who happen to publish on the same platform.
    """
    d = (domain or "").lower().strip(".")
    return any(d == b or d.endswith("." + b) for b in INFRA_DOMAINS)


def _linkable(kind: str, value: str) -> bool:
    """True for keys that may link signals to founders (non-empty, not infra)."""
    return bool(value) and not (kind == "domain" and is_infra_domain(value))


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
            if _linkable(t, v):  # a stored infra domain must never match/merge
                key_index[(t, v)] = f["id"]

    resolutions: list[tuple[str, str, str]] = []
    dropped: list[tuple[str, str]] = []

    for it in items:
        raw = {t: v for t, v in it["keys"].items() if v}
        present = {t: v for t, v in raw.items() if _linkable(t, v)}
        if len(present) < 2:
            # If stripping an infra domain is what pushed it below the bar, say so.
            reason = ("infra_domain_not_linking" if len(raw) >= 2 and len(raw) > len(present)
                      else "insufficient_entity_keys")
            dropped.append((it["signal_id"], reason))
            _droplog(conn, it["signal_id"], reason, raw)
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
