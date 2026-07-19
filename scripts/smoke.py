"""End-to-end smoke harness: exercises every interactive path a judge can click.

Usage: python scripts/smoke.py [--base-url http://localhost:8000]

Fails loudly (non-zero exit) on any dead end. Run after every block and against
the deployed URL before submission. Uses a fixed company name so re-runs dedup
instead of accumulating junk founders.
"""
import argparse
import sys
import time

import httpx

FAIL = []


def check(name, ok, detail=""):
    mark = "ok " if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--skip-llm", action="store_true",
                    help="skip paths that need a live LLM key")
    args = ap.parse_args()
    c = httpx.Client(base_url=args.base_url, timeout=120)

    # 1. Static + seeded reads
    r = c.get("/")
    check("frontend served at /", r.status_code == 200)
    r = c.get("/api/theses")
    check("theses list", r.status_code == 200 and len(r.json()) >= 1)
    r = c.get("/api/founders")
    founders = r.json() if r.status_code == 200 else []
    check("founders list non-empty (seeded)", bool(founders), f"n={len(founders)}")
    r = c.get("/api/sourcing")
    check("sourcing feed", r.status_code == 200 and r.json()["founders"],
          f"droplog={r.json().get('droplog_count')}" if r.status_code == 200 else r.text)

    # 2. Memo + trace on a seeded founder (click-to-evidence chain)
    with_memo = [f for f in founders if f.get("has_memo")]
    check("at least one seeded memo", bool(with_memo))
    if with_memo:
        fid = with_memo[0]["id"]
        brief = c.get(f"/api/founders/{fid}").json()
        claims = brief.get("claims", [])
        check("memo has claims", bool(claims), f"n={len(claims)}")
        no_url = [cl["id"] for cl in claims if not cl.get("evidence_url")]
        check("every claim has evidence_url", not no_url, str(no_url[:5]))
        if claims:
            t = c.get(f"/api/trace/{fid}/{claims[0]['id']}")
            check("trace endpoint", t.status_code == 200
                  and t.json()["claim"]["evidence_url"])

    # 3. Inbound apply — the judge's own company must not dead-end: it must end in a
    # real memo (or an honest kill/error), watchable via GET /api/runs/{fid}.
    if not args.skip_llm:
        r = c.post("/api/apply", json={
            "company": "Smoke Test Co",
            "deck_text": "Smoke Test Co builds automated smoke detection for CI "
                         "pipelines. 5 design partners, $10K MRR, solo founder."})
        body = r.json()
        check("apply accepted", r.status_code == 200, str(body))
        check("apply screened (or surfaced error)",
              body.get("screened") or body.get("screen_error"),
              str(body.get("screen_error")))
        fid = body.get("founder_id")

        run, state, deadline = {}, None, time.time() + 300
        while time.time() < deadline:
            rr = c.get(f"/api/runs/{fid}")
            if rr.status_code != 200:
                break
            run = rr.json()
            state = run.get("state")
            if state in ("ok", "error"):
                break
            time.sleep(3)
        done_detail = next((s.get("detail") or "" for s in run.get("stages", [])
                            if s.get("stage") == "done"), "")
        check("apply run reached a terminal state", state in ("ok", "error"),
              f"state={state}")
        check("apply run finished without error", state == "ok", done_detail)
        if state == "ok" and "killed" in done_detail:
            check("apply run ended honestly (killed at first pass, no memo)",
                  not run.get("has_memo"), done_detail)
        elif state == "ok":
            check("memo exists after apply run", run.get("has_memo"), done_detail)
            brief = c.get(f"/api/founders/{fid}").json()
            check("apply memo is renderable", bool(brief.get("memo_md")),
                  f"decision={brief.get('decision')}")

        # 4. NL query on a NOVEL judge-typed query (never cached). Parse failures
        # come back 200 with an `error` sentence — that still counts as a failure here.
        r = c.get("/api/query", params={
            "q": f"technical founder, AI infra, enterprise traction {int(time.time())}"})
        qj = r.json() if r.status_code == 200 else {}
        check("novel NL query", r.status_code == 200 and not qj.get("error"),
              qj.get("error") or r.text[:120] if (r.status_code != 200 or qj.get("error"))
              else f"criteria={len(qj.get('criteria', []))}")

    # 5. Live scan — real adapter call, one source (needs network, not an LLM key)
    r = c.post("/api/scan", params={"source": "hn"})
    check("live scan endpoint", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        sj = r.json()
        check("scan payload sane",
              "hn" in sj.get("counts", {}) and "resolved" in sj and "dropped" in sj,
              str({k: sj.get(k) for k in ("counts", "resolved", "dropped",
                                          "new_signals")}))
    r = c.get("/api/quality")
    check("data-quality endpoint exists", r.status_code != 404,
          f"status={r.status_code}")

    # 6. Scoring transparency — the methodology endpoint backing every InfoTip
    r = c.get("/api/methodology")
    mj = r.json() if r.status_code == 200 else {}
    check("methodology endpoint (global)", r.status_code == 200
          and all(k in mj for k in ("signal", "coverage", "axes", "trust")),
          f"status={r.status_code}")
    if with_memo:
        r = c.get(f"/api/methodology?founder_id={with_memo[0]['id']}")
        check("methodology endpoint (per-founder)", r.status_code == 200
              and "for_founder" in r.json(), f"status={r.status_code}")

    # 7. Sourcing network — reference graph + live channel yield join
    r = c.get("/api/network")
    nj = r.json() if r.status_code == 200 else {}
    check("network endpoint", r.status_code == 200
          and bool(nj.get("startups")) and bool(nj.get("channel_intelligence")),
          f"status={r.status_code}, startups={len(nj.get('startups', []))}")

    print(f"\n{len(FAIL)} failure(s)" if FAIL else "\nall smoke checks passed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
