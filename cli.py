"""VC Brain pipeline entrypoint.

Block 1 exposes:
  init  — create the on-disk vc_brain.db with the Memory schema
  demo  — exercise the Block 1 acceptance gate in an in-memory DB (idempotent)

Later blocks add: scan, screen, diligence, memo.
"""
import argparse

from app import config, llm
from app.memory import db, ingest
from app.memory.models import Claim, Founder, Signal
from app.screening import axes as axes_mod
from app.screening import thesis as thesis_mod


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
    """Outbound scanner: thesis-driven queries across all adapters -> Memory ->
    entity resolution. --watch loops and auto-screens founders whose new signals
    cross the conviction threshold (brief: "signals crossing a conviction threshold
    on their own"), then drafts Activate outreach."""
    import time as _time

    from app import activate as activate_mod
    from app.sources import scanner

    replay = config.replay_enabled(args.replay)
    conn = db.connect()
    db.init_db(conn)
    thesis = thesis_mod.load_thesis(args.thesis)
    topics = scanner.topics_for(thesis, args.topic)
    rounds = args.rounds if args.watch else 1

    for rnd in range(1, rounds + 1):
        if args.watch:
            print(f"\n--- watch round {rnd}/{rounds} (topics from thesis "
                  f"{thesis.name!r}: {topics}) ---")
        result = scanner.run_scan(conn, topics, replay=replay)
        for name, n in result["counts"].items():
            print(f"[{name}] {n}")
        reasons = {}
        for _, r in result["dropped"]:
            reasons[r] = reasons.get(r, 0) + 1
        print(f"[resolve] {result['resolved']} signals resolved -> "
              f"{result['founders']} founders; {len(result['dropped'])} "
              f"drop-logged {reasons}")

        # Persistent Founder Score: append a history point for founders whose record
        # just changed (deterministic, no LLM — cheap on every scan).
        from datetime import datetime, timezone

        from app.memory import founder_score
        fresh_all = scanner.newly_resolved_founders(conn, result["new_signal_ids"])
        now = datetime.now(timezone.utc).isoformat()
        for fid, _ in fresh_all:
            founder_score.recompute(conn, fid, "scan", now=now)
        if fresh_all:
            print(f"[founder-score] appended history point for {len(fresh_all)} founders")

        if args.watch:
            fresh = fresh_all
            print(f"[watch] {len(fresh)} founders gained signals this round")
            if fresh and not replay and llm.provider() is None:
                print("[watch] no LLM key — skipping conviction screening")
            elif fresh:
                for fid, n_new in fresh[:args.max_screens]:
                    res = axes_mod.screen(conn, fid, thesis, replay=replay)
                    if res["killed"]:
                        print(f"[screen] {fid} (+{n_new} signals) KILLED: "
                              f"{res['kill_reason']}")
                        continue
                    best = max(a["score"] for a in res["axes"].values())
                    print(f"[screen] {fid} (+{n_new} signals) best axis {best}/10")
                    if best >= args.threshold:
                        d = activate_mod.draft(conn, fid, thesis.name, replay=replay)
                        print(f"[ACTIVATE] {fid} crossed conviction threshold "
                              f"{args.threshold} — outreach drafted:\n"
                              f"  Subject: {d.subject}\n  Cites: {d.cited_signal_url}")
        if args.watch and rnd < rounds:
            print(f"[watch] sleeping {args.interval}s")
            _time.sleep(args.interval)


def cmd_velocity(args) -> None:
    """Cold-start instrument: fetch trailing-6-week commit cadence for the top
    thesis-matched GitHub founders, ingest as signals, recompute Founder Scores."""
    from datetime import datetime, timezone

    from app.memory import founder_score
    from app.sources import velocity

    replay = config.replay_enabled(args.replay)
    conn = db.connect()
    db.init_db(conn)
    rows = conn.execute(
        "SELECT r.founder_id fid, COUNT(*) n FROM resolutions r "
        "JOIN signals s ON s.id = r.signal_id WHERE s.source='github' "
        "GROUP BY r.founder_id ORDER BY n DESC LIMIT ?", (args.top,)).fetchall()
    now = datetime.now(timezone.utc).isoformat()
    for r in rows:
        try:
            v = velocity.fetch(conn, r["fid"], replay=replay)
        except Exception as e:  # rate limit / replay miss on one repo: keep going
            print(f"[velocity] {r['fid']}: skipped ({type(e).__name__}: {e})")
            continue
        if v:
            cur = founder_score.recompute(conn, r["fid"], "velocity", now=now)
            print(f"[velocity] {r['fid']}: {v['commits_6w']} commits / "
                  f"{v['active_days']} active days (6w) -> score {cur['score']}")


def cmd_activate(args) -> None:
    """Draft outreach for a founder, citing the signal that triggered the interest."""
    from app import activate as activate_mod
    replay = config.replay_enabled(args.replay)
    conn = db.connect()
    db.init_db(conn)
    if not replay and llm.provider() is None:
        print("activate makes a live LLM call — set a key, or use --replay.")
        return
    thesis = thesis_mod.load_thesis(args.thesis)
    d = activate_mod.draft(conn, args.founder, thesis.name, replay=replay)
    print(f"Subject: {d.subject}\n\n{d.body}\n\n[cites triggering signal: "
          f"{d.cited_signal_url}]")


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
    if not replay and llm.provider() is None:
        print("screen makes live LLM calls — set OPENAI_API_KEY (or ANTHROPIC_API_KEY) "
              "first (then re-run with --replay to reuse the cached run).")
        return
    thesis = thesis_mod.load_thesis(args.thesis)
    founder_id = args.founder or _pick_founder(conn)
    if not founder_id:
        print("no resolved founders in Memory — run `scan` first")
        return
    if not conn.execute("SELECT 1 FROM founders WHERE id=?", (founder_id,)).fetchone():
        print(f"unknown founder '{founder_id}' — not in Memory")
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


def cmd_diligence(args) -> None:
    """Full diligence on a fixture founder: workers -> ledger -> adjudication debate ->
    recommendation debate -> synthesizer -> validator + critic -> memo."""
    replay = config.replay_enabled(args.replay)
    conn = db.connect()
    db.init_db(conn)
    if not replay and llm.provider() is None:
        print("diligence makes live LLM calls — set OPENAI_API_KEY (or ANTHROPIC_API_KEY).")
        return
    from app.diligence import loader, pipeline
    founder_id = loader.load_fixture(conn, args.fixture, replay=replay)
    thesis = thesis_mod.load_thesis(args.thesis)
    result = pipeline.run_diligence(conn, founder_id, thesis, replay=replay)
    v = result["violations"]
    print(f"\n=== Diligence: {founder_id} | {thesis.name} ===")
    print(f"claims={result['claims']} contested(adjudicated)={result['contested']} "
          f"decision={result['recommendation'].decision} "
          f"validator_clean={v.ok} (unknown_ids={v.unknown_ids})")
    if args.print_memo:
        print("\n" + result["memo"])


def cmd_decision(args) -> None:
    """Assemble the decision brief: recommendation + per-axis (unblended) + gap rendering
    + latency strip + memo. Runs diligence first (cached in --replay = zero cost)."""
    replay = config.replay_enabled(args.replay)
    conn = db.connect()
    db.init_db(conn)
    if not replay and llm.provider() is None:
        print("decision runs diligence (live LLM) — set OPENAI_API_KEY, or use --replay.")
        return
    from app.decision import decision as dec
    from app.diligence import loader, pipeline
    founder_id = loader.load_fixture(conn, args.fixture, replay=replay)
    thesis = thesis_mod.load_thesis(args.thesis)
    pipeline.run_diligence(conn, founder_id, thesis, replay=replay)
    print(dec.render(dec.build(conn, founder_id, thesis)))


def main() -> None:
    parser = argparse.ArgumentParser(prog="vc-brain")
    parser.add_argument("--replay", action="store_true", help="read only from cache")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="create vc_brain.db").set_defaults(func=cmd_init)
    sub.add_parser("demo", help="run the Block 1 gate demo").set_defaults(func=cmd_demo)
    p_scan = sub.add_parser("scan", help="thesis-driven outbound scanner into Memory")
    p_scan.add_argument("--thesis", default="config/thesis_preseed_ai_infra.yaml")
    p_scan.add_argument("--topic", help="override: scan a single topic instead of "
                                        "the thesis topics")
    p_scan.add_argument("--watch", action="store_true",
                        help="continuous mode: rescan + auto-screen new founders")
    p_scan.add_argument("--rounds", type=int, default=3, help="watch rounds")
    p_scan.add_argument("--interval", type=int, default=300,
                        help="seconds between watch rounds")
    p_scan.add_argument("--threshold", type=float, default=7.5,
                        help="conviction threshold (best axis score) for Activate")
    p_scan.add_argument("--max-screens", type=int, default=3,
                        help="max founders screened per watch round")
    p_scan.set_defaults(func=cmd_scan)
    p_vel = sub.add_parser("velocity", help="fetch commit cadence for top GitHub founders")
    p_vel.add_argument("--top", type=int, default=15)
    p_vel.set_defaults(func=cmd_velocity)
    p_act = sub.add_parser("activate", help="draft outreach citing the triggering signal")
    p_act.add_argument("--founder", required=True)
    p_act.add_argument("--thesis", default="config/thesis_preseed_ai_infra.yaml")
    p_act.set_defaults(func=cmd_activate)
    p_screen = sub.add_parser("screen", help="3-axis screen through a thesis lens")
    p_screen.add_argument("--founder", help="founder id (default: most-signalled)")
    p_screen.add_argument("--thesis", default="config/thesis_preseed_ai_infra.yaml")
    p_screen.set_defaults(func=cmd_screen)
    p_dil = sub.add_parser("diligence", help="full diligence + memo on a fixture founder")
    p_dil.add_argument("--fixture", default="founder_b_corevance")
    p_dil.add_argument("--thesis", default="config/thesis_preseed_ai_infra.yaml")
    p_dil.add_argument("--print-memo", action="store_true", help="print the full memo")
    p_dil.set_defaults(func=cmd_diligence)
    p_dec = sub.add_parser("decision", help="decision brief (rec + axes + gaps + latency)")
    p_dec.add_argument("--fixture", default="founder_b_corevance")
    p_dec.add_argument("--thesis", default="config/thesis_preseed_ai_infra.yaml")
    p_dec.set_defaults(func=cmd_decision)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
