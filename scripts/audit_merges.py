"""Audit (and optionally fix) infra-domain false merges in any VC Brain DB.

Report mode (default) sweeps for:
  (i)   founders whose resolved signals conflict on same-type identity keys
        (e.g. 20 distinct hn authors under one founder — linked only through a
        non-person key such as github.com),
  (ii)  founders whose stored entity_keys contain a blacklisted infra domain,
  (iii) founders with signals from >1 source whose non-domain keys never co-occur.

--fix (only acts on founders implicated by (i)/(ii)):
  * DELETE their resolutions rows (allowed; signals/founders are NEVER deleted),
  * re-derive each signal's keys from its stored row and re-run resolution so
    legitimately-linked signals re-attach,
  * droplog the rest with reason "unlinked: infra-domain merge",
  * rebuild the founder's entity_keys from keys backed by still-resolved signals
    (an orphaned founder keeps {} — honest: no resolved evidence backs any key),
  * display names: a bare-handle name (equal to a github/hn key or a re-derived
    handle of its signals) becomes "@handle". No human name is ever guessed.

Usage: python scripts/audit_merges.py [--db PATH] [--fix]
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.memory import db, resolve  # noqa: E402
from app.memory.resolve import INFRA_DOMAINS  # noqa: E402

UNLINK_REASON = "unlinked: infra-domain merge"

_GH_OWNER = re.compile(r"github\.com/([A-Za-z0-9_-]+)")
_HN_AUTHOR = re.compile(r"author=(\S+)")
_ARXIV_AUTHORS = re.compile(r"authors=([^|]+)")
_YC_SLUG = re.compile(r"ycombinator\.com/companies/([a-z0-9-]+)")
_PH_MAKER = re.compile(r"maker=([^|]+)")


def rederive_keys(row) -> dict:
    """Best-effort identity keys recomputed from a stored signal row alone.

    Adapter-derived domain keys (repo homepage, submitted-URL domain) are not
    persisted on the signal, so they cannot be reconstructed here — a signal that
    only linked via a domain re-derives to a single key and stays unlinked.
    """
    src, url, content = row["source"], row["source_url"] or "", row["content"] or ""
    if src == "github":
        m = _GH_OWNER.search(url)
        return {"github": m.group(1)} if m else {}
    if src == "hn":
        m = _HN_AUTHOR.search(content)
        return {"hn": m.group(1)} if m else {}
    if src == "yc":
        m = _YC_SLUG.search(url)
        return {"yc": m.group(1)} if m else {}
    if src == "arxiv":
        m = _ARXIV_AUTHORS.search(content)
        first = m.group(1).split(",")[0].strip() if m else ""
        slug = re.sub(r"[^a-z0-9]+", "-", first.lower()).strip("-")
        return {"arxiv": slug} if slug else {}
    if src == "producthunt":
        m = _PH_MAKER.search(content)
        return {"name": m.group(1).strip()} if m else {}
    return {}


def _founders(conn):
    return [(r["id"], r["name"], json.loads(r["entity_keys"] or "{}"))
            for r in conn.execute("SELECT id, name, entity_keys FROM founders").fetchall()]


def _resolved_signals(conn, fid):
    return conn.execute(
        "SELECT s.id, s.source, s.source_url, s.content FROM resolutions r "
        "JOIN signals s ON s.id = r.signal_id WHERE r.founder_id = ?", (fid,)).fetchall()


def sweep(conn) -> dict:
    """Return {"findings": [...], "renames": [...]}; read-only."""
    findings, renames = [], []
    for fid, name, keys in _founders(conn):
        rows = _resolved_signals(conn, fid)
        derived = [(r["id"], rederive_keys(r)) for r in rows]

        # (ii) blacklisted domain stored as an entity key
        bad_keys = {t: v for t, v in keys.items() if v and v.lower() in INFRA_DOMAINS}
        # (i) same-type key conflicts across this founder's signals (person keys only)
        by_type: dict[str, set] = {}
        for _, dk in derived:
            for t, v in dk.items():
                if t in ("github", "hn"):
                    by_type.setdefault(t, set()).add(v)
        conflicts = {t: sorted(vs) for t, vs in by_type.items() if len(vs) > 1}
        # (iii) >1 source, non-domain keys never co-occur (no shared handle value)
        sources = {r["source"] for r in rows}
        disjoint = False
        if len(sources) > 1:
            vals = [set(dk.values()) for _, dk in derived if dk]
            disjoint = bool(vals) and not set.intersection(*vals)

        if bad_keys or conflicts or disjoint:
            chain = "; ".join(
                f"{sid} ({', '.join(f'{t}={v}' for t, v in dk.items()) or 'no keys'})"
                for sid, dk in derived[:6])
            if len(derived) > 6:
                chain += f"; ... {len(derived) - 6} more"
            findings.append({
                "founder_id": fid, "name": name, "entity_keys": keys,
                "resolved_signals": len(rows),
                "blacklisted_keys": bad_keys, "key_conflicts": conflicts,
                "multi_source_disjoint": disjoint, "link_chain": chain,
                "fixable": bool(bad_keys or conflicts),
                "proposed_action": ("unlink + re-resolve" if bad_keys or conflicts
                                    else "review (report-only heuristic)"),
            })

        # display-name pass: bare handle -> "@handle"
        handles = {v for t, v in keys.items() if t in ("github", "hn") and v}
        handles |= {v for _, dk in derived for t, v in dk.items() if t in ("github", "hn")}
        if name in handles and not name.startswith("@"):
            renames.append((fid, name, "@" + name))
    return {"findings": findings, "renames": renames}


def fix(conn) -> dict:
    """Apply the unlink/re-resolve/rename pass. Never deletes signals or founders."""
    now = datetime.now(timezone.utc).isoformat()
    report = sweep(conn)  # pre-fix snapshot drives both unlinks and renames
    changed = {}
    for f in report["findings"]:
        if not f["fixable"]:
            continue
        fid = f["founder_id"]
        rows = _resolved_signals(conn, fid)
        conn.execute("DELETE FROM resolutions WHERE founder_id = ?", (fid,))
        conn.commit()
        items = [{"signal_id": r["id"], "label": r["content"][:60],
                  "keys": rederive_keys(r)} for r in rows]
        relink = [it for it in items
                  if len({t: v for t, v in it["keys"].items()
                          if resolve._linkable(t, v)}) >= 2]
        summary = resolve.resolve(conn, relink) if relink else {"resolved": 0}
        relinked_ids = {it["signal_id"] for it in relink}
        unlinked = 0
        for it in items:
            if it["signal_id"] in relinked_ids:
                continue
            conn.execute("INSERT INTO droplog (signal_id, reason, entity_keys, "
                         "logged_at) VALUES (?,?,?,?)",
                         (it["signal_id"], UNLINK_REASON, json.dumps(it["keys"]), now))
            unlinked += 1
        # entity_keys must be backed by a signal still resolved to this founder.
        backed: dict[str, str] = {}
        for r in _resolved_signals(conn, fid):
            backed.update(rederive_keys(r))
        conn.execute("UPDATE founders SET entity_keys = ?, last_updated = ? "
                     "WHERE id = ?", (json.dumps(backed), now, fid))
        conn.commit()
        changed[fid] = {"before": f["resolved_signals"],
                        "re_resolved": summary["resolved"], "unlinked": unlinked,
                        "entity_keys_before": f["entity_keys"],
                        "entity_keys_after": backed}
    for fid, old, new in report["renames"]:
        conn.execute("UPDATE founders SET name = ?, last_updated = ? WHERE id = ?",
                     (new, now, fid))
    conn.commit()
    return {"fixed": changed, "renamed": report["renames"],
            "report_only": [f["founder_id"] for f in report["findings"]
                            if not f["fixable"]]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=None, help="DB path (default: config.DB_PATH)")
    ap.add_argument("--fix", action="store_true", help="apply unlink/rename fixes")
    args = ap.parse_args()
    conn = db.connect(args.db)

    if not args.fix:
        report = sweep(conn)
        if not report["findings"] and not report["renames"]:
            print("clean: no infra-domain merges, key conflicts, or bare-handle names")
            return
        for f in report["findings"]:
            print(f"[{f['proposed_action']}] {f['founder_id']} "
                  f"(name={f['name']!r}, {f['resolved_signals']} resolved signals)")
            print(f"  entity_keys: {f['entity_keys']}")
            if f["blacklisted_keys"]:
                print(f"  blacklisted keys: {f['blacklisted_keys']}")
            if f["key_conflicts"]:
                print(f"  key conflicts: {f['key_conflicts']}")
            if f["multi_source_disjoint"]:
                print("  multi-source signals with disjoint non-domain keys")
            print(f"  link chain: {f['link_chain']}")
        for fid, old, new in report["renames"]:
            print(f"[rename] {fid}: {old!r} -> {new!r}")
    else:
        out = fix(conn)
        for fid, c in out["fixed"].items():
            print(f"fixed {fid}: {c['before']} resolved -> {c['re_resolved']} "
                  f"re-resolved, {c['unlinked']} unlinked to droplog; "
                  f"entity_keys {c['entity_keys_before']} -> {c['entity_keys_after']}")
        for fid, old, new in out["renamed"]:
            print(f"renamed {fid}: {old!r} -> {new!r}")
        if out["report_only"]:
            print(f"left for review (heuristic-only): {out['report_only']}")
        if not out["fixed"] and not out["renamed"]:
            print("clean: nothing to fix")


if __name__ == "__main__":
    main()
