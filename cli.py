"""VC Brain pipeline entrypoint.

Block 1 exposes:
  init  — create the on-disk vc_brain.db with the Memory schema
  demo  — exercise the Block 1 acceptance gate in an in-memory DB (idempotent)

Later blocks add: scan, screen, diligence, memo.
"""
import argparse

from app import config
from app.memory import db, ingest
from app.memory.models import Claim, Founder, Signal


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


def main() -> None:
    parser = argparse.ArgumentParser(prog="vc-brain")
    parser.add_argument("--replay", action="store_true", help="read only from cache")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="create vc_brain.db").set_defaults(func=cmd_init)
    sub.add_parser("demo", help="run the Block 1 gate demo").set_defaults(func=cmd_demo)

    args = parser.parse_args()
    config.replay_enabled(args.replay)  # thread the flag (no live calls in Block 1)
    args.func(args)


if __name__ == "__main__":
    main()
