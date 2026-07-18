"""VC Brain pipeline entrypoint.

Block 1 exposes:
  init  — create the on-disk vc_brain.db with the Memory schema
  demo  — exercise the Block 1 acceptance gate in an in-memory DB (idempotent)

Later blocks add: scan, screen, diligence, memo.
"""
import argparse
import os

from app import config
from app.memory import db, ingest, resolve
from app.memory.models import Claim, Founder, Signal
from app.screening import axes as axes_mod
from app.screening import thesis as thesis_mod
from app.sources import arxiv, github, hn


def cmd_init(_args) -> None:
    conn = db.connect()
    db.init_db(conn)
    print(f"initialized {config.DB_PATH}")


def cmd_demo(_args) -> None:
    """Demonstrate the three Block 1 gate properties in an in-memory DB."""
    conn = db.connect(":memory:")
    db.init_db(conn)

    ingest.upsert_founder(conn, Founder(id="founder-b", name="Devin Marsh"))

    # 1) Dedup rejects an identical signal.
    sig = Signal(source="deck", source_url="fixtures/founder_b_corevance/deck-summary.txt",
                 content="DataLoom acquired by Cisco, 2021", founder_id="founder-b")
    id1, ins1 = ingest.ingest_signal(conn, sig)
    id2, ins2 = ingest.ingest_signal(conn, sig)  # same content -> duplicate
    print(f"[dedup] first insert={ins1} id={id1} | second insert={ins2} id={id2} "
          f"(duplicate rejected: {not ins2 and id1 == id2})")

    # 2) Negative result stored as a first-class claim, with the search URL as source.
    neg = Claim(
        id="dd-02", axis="founder", stance="contradicts",
        text="No Form D exists for DataLoom's claimed $4M seed.",
        evidence="EDGAR full-text search for DataLoom Form D: no filing found.",
        source_url="https://efts.sec.gov/LATEST/search-index?q=%22DataLoom%22&forms=D",
        source_type="web", corroboration="corroborated", trust=0.9,
        observed_at="2026-07-18",
    )
    ingest.store_claim(conn, "founder-b", neg, signal_ids=[id1])
    stored = ingest.get_claims(conn, "founder-b")[0]
    print(f"[negative-result claim] {stored.id} stance={stored.stance} "
          f"source_url={stored.source_url}")

    # 3) Append-only: deleting a signal is refused by the DB trigger.
    try:
        conn.execute("DELETE FROM signals WHERE id = ?", (id1,))
        print("[append-only] FAIL: delete was allowed")
    except Exception as e:  # sqlite3.IntegrityError from RAISE(ABORT)
        print(f"[append-only] delete refused: {e}")

    total = conn.execute("SELECT COUNT(*) c FROM signals").fetchone()["c"]
    print(f"[state] signals in table: {total} (append-only, nothing discarded)")


def cmd_scan(args) -> None:
    """Outbound scanner: GitHub + HN (+ arXiv) -> Memory, then entity resolution."""
    replay = config.replay_enabled(args.replay)
    conn = db.connect()
    db.init_db(conn)

    items = []
    for name, fn, arg in [("github", github.scan, args.topic),
                          ("hn", hn.scan, args.query),
                          ("arxiv", arxiv.scan, args.query)]:
        if name == "arxiv" and not args.arxiv:
            continue
        try:
            found = fn(conn, arg, replay=replay)
            items += found
            print(f"[{name}] {len(found)} signals for {arg!r}")
        except Exception as e:  # a source failing must not sink the scan
            print(f"[{name}] skipped: {type(e).__name__}: {e}")

    summary = resolve.resolve(conn, items)
    dropped = summary["dropped"]
    reasons = {}
    for _, r in dropped:
        reasons[r] = reasons.get(r, 0) + 1
    print(f"[resolve] {summary['resolved']} signals resolved -> "
          f"{summary['founders']} founders; {len(dropped)} drop-logged {reasons}")


def _pick_founder(conn) -> str | None:
    row = conn.execute(
        "SELECT r.founder_id AS fid, COUNT(*) n FROM resolutions r "
        "GROUP BY r.founder_id ORDER BY n DESC LIMIT 1").fetchone()
    return row["fid"] if row else None


def cmd_screen(args) -> None:
    """Screen a founder on 3 independent axes through a thesis lens (never averaged)."""
    replay = config.replay_enabled(args.replay)
    conn = db.connect()
    db.init_db(conn)
    if not replay and not (os.environ.get("ANTHROPIC_API_KEY")
                           or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("screen makes live LLM calls — export ANTHROPIC_API_KEY first "
              "(then re-run with --replay to reuse the cached run).")
        return
    thesis = thesis_mod.load_thesis(args.thesis)
    founder_id = args.founder or _pick_founder(conn)
    if not founder_id:
        print("no resolved founders in Memory — run `scan` first")
        return

    result = axes_mod.screen(conn, founder_id, thesis, replay=replay)
    print(f"\n=== Screen: {founder_id} | thesis: {result['thesis']} ===")
    if result["killed"]:
        print(f"KILLED (first-pass): {result['kill_reason']}")
        return
    for axis, a in result["axes"].items():
        print(f"  {axis:8s}  score {a['score']:>4}/10  {a['trend']:<9} "
              f"[{a['stance']}]  cov {a['coverage']:.0%}  — {a['rationale']}")
    print("  (three axes shown side by side; no blended score by design)")


def main() -> None:
    parser = argparse.ArgumentParser(prog="vc-brain")
    parser.add_argument("--replay", action="store_true", help="read only from cache")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="create vc_brain.db").set_defaults(func=cmd_init)
    sub.add_parser("demo", help="run the Block 1 gate demo").set_defaults(func=cmd_demo)
    p_scan = sub.add_parser("scan", help="outbound scanner into Memory")
    p_scan.add_argument("--topic", default="llm", help="GitHub topic to scan")
    p_scan.add_argument("--query", default="agent", help="HN/arXiv query")
    p_scan.add_argument("--arxiv", action="store_true", help="also scan arXiv")
    p_scan.set_defaults(func=cmd_scan)
    p_screen = sub.add_parser("screen", help="3-axis screen through a thesis lens")
    p_screen.add_argument("--founder", help="founder id (default: most-signalled)")
    p_screen.add_argument("--thesis", default="config/thesis_preseed_ai_infra.yaml")
    p_screen.set_defaults(func=cmd_screen)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
