# Founder A — Tracewell (cold-start, sourced outbound)

Surfaced by the outbound scanner (GitHub velocity + Show HN), **not** inbound. Founder has not begun
fundraising. The record is thin because the founder is 21 and nine weeks into public work — not because
the work is weak. Recommendation target: **invest $100K, conditional on incorporation. Signal 7.8 /
Coverage 24%.**

## Profile

- **Founder handle:** `nferris` (GitHub), linked personal domain `tracewell.dev`. Age 21. Solo. No
  employment or education claims made anywhere public; no commercial experience; company **not
  incorporated**. Identity beyond public handles is unverified (this is the coverage gap, not a red flag).
- **Product — Tracewell:** open-source evaluation harness for LLM agent pipelines — regression testing for
  agent *behavior*, the way CI regression-tests code. Records agent traces, lets developers pin expected
  behaviors, and fails CI when behavior drifts. Works today with two major agent frameworks: **LangGraph**
  and **CrewAI** (verified against the repo's `examples/` directory).
- **Wedge → expansion (hypothesis, unproven):** open-source harness → hosted eval dashboard → enterprise
  compliance reporting for agent behavior.

## Raw signals

### GitHub — `github.com/nferris/tracewell`
- `source_url`: https://github.com/nferris/tracewell — `observed_at`: 2026-07-17
- Repo created **2026-05-14** (9 weeks old). Stars: **1,420**. External issue filers: **40+**.
- Commit cadence: **61 consecutive days with commits** (2026-05-16 → 2026-07-15).
- Tagged releases (3): `v0.1.0` 2026-05-28 · `v0.2.0` 2026-06-18 · `v0.3.0` 2026-07-09.
- Median issue response time: **< 8 hours** (computed over 40+ issues).
- Last 20 merged PRs: **11 authored by external contributors** (not `nferris`).
- README contains a benchmark table claiming drift-detection accuracy — **not independently replicated**
  (this is open item open-03).
- Identity link: repo profile links `tracewell.dev`, the same domain in the Show HN submission → identity
  match. `source_url`: https://github.com/nferris

### Hacker News — Show HN
- `source_url`: https://news.ycombinator.com/item?id=48210077 — `observed_at`: 2026-06-24
- "Show HN: Tracewell – CI-style regression tests for LLM agent behavior" by `nferris`.
- **890 points**, **#2 Show HN of its day**. Submitter domain `tracewell.dev` matches GitHub identity.

### Package registry — PyPI `tracewell`
- `source_url`: https://pypi.org/project/tracewell/ — `observed_at`: 2026-07-17
- **~3,100 weekly downloads** (registry stats — single source, no external corroboration).

### Market (single-source)
- Agent-eval category is early; no dominant incumbent. `source_url`:
  https://news.ycombinator.com/item?id=48210077 (comment thread) — single source [mkt-02].
- Competitive risk: LangSmith / Braintrust could absorb the feature. [risk-01]

## Entity-resolution drop-log (Block 2 must reproduce)
- **6 signals discarded**: same-name GitHub accounts (`nferris` collides with unrelated accounts on other
  repos). Failed the ≥2-entity-key co-occurrence test → logged, excluded, **not** attached to this founder.

## Score & outlook
- Signal **7.8** / Coverage **24%**. Outcome view: 45% quiet failure, 40% modest, 15% meaningful company.
- Open items: **open-01** founder identity/background beyond public handles; **open-02** whether prior
  collaborators would co-found; **open-03** independent replication of the README benchmark table.
- "What would change our mind": two weeks of stalled commit cadence, or evidence the benchmark doesn't
  replicate.

## Claim-ID cross-reference (→ target-memos.md MEMO 1)
| Claim | Fact | Source | Tier |
|---|---|---|---|
| src-01 | Outbound-sourced; Show HN authorship matches GitHub identity via `tracewell.dev` | HN + GitHub | corr |
| prod-01 | OSS eval harness = CI regression testing for agent behavior | GitHub README | corr |
| prod-02 | Works with LangGraph + CrewAI | repo `examples/` | corr |
| trac-01 | Repo 9 wks old, 1,420 stars, 40+ external issue filers | GitHub | corr |
| trac-02 | #2 Show HN (890 pts); 11/20 last merged PRs external | HN + GitHub | corr |
| trac-03 | ~3,100 weekly downloads | PyPI (single source) | single |
| team-02 | 61 consecutive commit days, 3 releases, median issue response < 8h | GitHub | corr |
| team-04 | Solo, no commercial experience, not incorporated | absence of public claims | corr |
| mkt-02 | Agent-eval category early, no dominant incumbent | HN thread (single) | single |
| risk-01 | LangSmith/Braintrust could absorb | inference from market | single |
| hyp-01 | OSS → hosted dashboard → enterprise compliance motion | inferred | inferred |
| open-01/02/03 | identity · co-founders · benchmark replication | DD open items | — |
