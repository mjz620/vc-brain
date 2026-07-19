# Judge Evaluation — VC Brain (adversarial audit, 2026-07-18)

Produced by stress-testing the running app against docs/challenge-brief.pdf.
Treat every finding as verified fact; each was reproduced live.

## Headline verdicts

### 1. Live scraping: real scrapers, real data — NOT live in the product
- `app/sources/{github,hn,arxiv,producthunt,yc}.py` make real httpx calls; cache
  holds authentic payloads (e.g. repo `affaan-m/ECC`, dependabot commits 2026-06-29).
- No LinkedIn scraping (guardrail respected).
- BUT: no scan endpoint exists in `server.py`. `/api/sourcing` is a pure DB read.
  Live scraping happens only via `cli.py scan` at DB-build time, and
  `scripts/rebuild_demo.py` runs `replay=True` (cache, not network). A judge
  clicking through the site generates zero live source calls.

### 2. Interactivity: live surface collapses to pre-baked fixtures (verified)
| Action performed | Result |
|---|---|
| POST /api/apply "NimbusForge" (novel deck) | stored, `screened: false` — no axes, no memo, dead end |
| NL query (novel compound query) | HTTP 422 "no cached response for this request" |
| Activate on novel founder | fails unless pre-cached |
| Switch company in Diligence/Decision | no control exists |

Root cause: `.env` is never loaded — no `load_dotenv()` anywhere in `app/`.
`llm.provider()` returns None in the server; apply→screen silently swallows the
exception (`app/server.py` `except Exception: pass`), NL query 422s.

### 3. No way to change company mid-pipeline (confirmed)
`Diligence.tsx:37` and `Decision.tsx:22` gate the founder picker behind
`if (!founderId)`. After selection: no switcher, no reset. Only 3 companies
(Tracewell, Parcelmind, Corevance) have memos.

## Rubric scorecard
| Criterion | Weight | Grade | Key notes |
|---|---|---|---|
| Data Architecture & Intelligence | 30% | B | Real multi-source ingestion, dedup, append-only signals, drop-log, negative results as claims, cold-start handled. Deductions: arXiv 28 signals → 0 resolved (dead channel); false-merge — `founder-armanified` = `hn:kamranahmed_se` + `domain:github.com` (two unrelated people; `github.com` used as linking key). |
| Intelligent Analysis & Trust | 25% | A– | Strongest pillar. Per-claim Trust Score, corroboration tiers, contradiction-first memo, prosecutor→defender→judge adjudication, no-LLM mechanical validator, gaps render "not disclosed." DO NOT REFACTOR. |
| Investment Utility & Execution | 30% | C+ | Seeded memos genuinely act-on-able (divergent axes, recommendation, latency strip). But utility gated to 3 pre-baked companies; an investor cannot run the tool on a new opportunity. |
| UX & Design | 15% | B– | Clean pipeline nav, click-to-evidence, trace panels. Undercut by dead-end apply, raw 422s, no company switcher, "armanified" cosmetic leak. |

Composite ≈ B (72–76%).

## Five fixes ranked by score impact
1. Load `.env` (un-breaks apply-screen, NL query, activate — the whole interactive surface).
2. Make Apply run the pipeline end-to-end with surfaced progress/errors.
3. Live "Scan now" button calling real adapters (rate-limited) — make the live
   claim demonstrable, not architectural.
4. Persistent company switcher across Diligence/Decision.
5. Entity resolution: blacklist infra domains as linking keys; fix or honestly
   label arXiv's 0% resolution; fix the armanified false-merge.
