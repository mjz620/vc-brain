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

    # 3. Inbound apply — the judge's own company must not dead-end
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

        # 4. NL query on a NOVEL judge-typed query (never cached)
        r = c.get("/api/query", params={
            "q": f"technical founder, AI infra, enterprise traction {int(time.time())}"})
        check("novel NL query", r.status_code == 200,
              r.text[:120] if r.status_code != 200 else
              f"criteria={len(r.json().get('criteria', []))}")

    # 5. Interactive endpoints added by later blocks (must exist, may be gated)
    r = c.post("/api/scan", params={"source": "hn"})
    check("live scan endpoint exists", r.status_code != 404,
          f"status={r.status_code}")
    r = c.get("/api/quality")
    check("data-quality endpoint exists", r.status_code != 404,
          f"status={r.status_code}")

    print(f"\n{len(FAIL)} failure(s)" if FAIL else "\nall smoke checks passed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
