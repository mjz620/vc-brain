# Demo Fixtures — Ground Truth

Three synthetic founders (spec §4). These files are the **source of truth** the pipeline ingests.
Every claim ID and number in `docs/target-memos.md` traces back to a fact stated here — the fixtures
*produce* the memos, so the two must stay consistent.

**Integrity rule (CLAUDE.md guardrail):** once approved, numbers/dates/names here are sacred. Never
regenerate them. The Corevance contradictions must keep contradicting. If a fixture must change, flag it.

Each `profile.md` has:
- **Profile** — the founder/company narrative.
- **Raw signals** — what each source (github|hn|arxiv|web|deck) would return, with `source_url` +
  `observed_at`. Block 2 ingests these in `--replay`; Block 4 workers cite them.
- **Seeded contradictions / red-team bait** — the exact facts that must fail verification.
- **Claim-ID cross-reference** — maps each `target-memos.md` claim ID to the fact + source that backs it.

| Founder | Company | Track | Recommendation | Signal / Coverage |
|---|---|---|---|---|
| A | Tracewell | outbound (cold-start) | invest, conditional on incorporation | 7.8 / 24% |
| B | Corevance | inbound (credentialed) | **pass** — 2 contradictions | 5.4 / 81% |
| C | Parcelmind | inbound | invest, conditional on 1 reference call | 6.9 / 64% |

Reference "today" for all `observed_at`/relative dates: **2026-07-18**.
