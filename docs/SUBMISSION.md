# VC Brain — Submission Write-up (draft, mirror of the four rubric headings)

One sentence: **an evidence-first sourcing and diligence engine that finds founders
before they fundraise, scores what is verifiable rather than who is connected, and
produces a gap-honest $100K memo in minutes.**

Run it: `python scripts/rebuild_demo.py` (deterministic from the committed replay
cache, <1s), then `cd frontend && npm run build && uvicorn app.server:app`.

---

## Data Architecture and Intelligence (30%)

- **Sourcing goes furthest** (per the brief's own priority): five live outbound
  channels — GitHub repo velocity, Hacker News Show HN, arXiv, ProductHunt launches,
  Y Combinator cohorts — driven by the thesis config's topics, not hand-typed queries.
  `scan --watch` re-scans continuously, auto-screens founders whose new signals cross
  a conviction threshold, and drafts **Activate** outreach that is mechanically forced
  to cite the exact triggering signal URL (a draft citing anything else is rejected).
- **Memory discards nothing**: append-only signals table enforced by SQLite triggers;
  SHA-256 dedup; ≥2-entity-key resolution with a drop-log (37 unresolved signals
  retained, visible in the UI). 180 signals → 113 resolved → 97 founders in the demo DB.
- **Cold-start is the design center, not an afterthought**: execution velocity
  (trailing-6-week commit cadence) is fetched per founder and scored; a thin record
  gets a **low-coverage flag, not a low score**. Tracewell — 9 weeks old, solo,
  unincorporated — reads *Signal 8.4 / Coverage 46%* and gets an invest-conditional
  memo; the credential-heavy Corevance reads *Signal 4.6 / Coverage 92%* and gets a pass.
  Coverage and signal moving independently is the equitable-allocation argument on one screen.
- **Founder Score** (FAQ 6): persistent per-person record in Memory — deterministic
  dimensions (execution velocity, community pull, domain breadth, integrity, verified
  depth), append-only history, never resets — fed into the Founder axis as one input,
  distinct from the per-opportunity screen.
- **Multi-attribute NL query** (MVP 3): "technical founder, AI infra, enterprise
  traction, no prior VC backing, top-tier accelerator" parses in one pass into typed
  criteria; the criterion Memory cannot evaluate ("no prior VC backing") is **flagged
  and ignored — never silently guessed**.

## Intelligent Analysis and Trust (25%)

- **Trust Score is per claim** (FAQ 7): every claim carries corroboration tier +
  trust (self-reported hard-capped at 0.6). Demo ledger: 27 corroborated (avg 0.85),
  15 single-source (0.60), 17 self-reported (0.42), 7 contradicted (0.12) — the
  tiering separates cleanly.
- **Contested claims go to trial**: prosecutor → defender → judge debate per claim;
  the judge's verdict overrides the mechanical rubric and the full transcript is
  persisted and rendered (20 adjudications in the demo DB).
- **Both seeded Corevance contradictions are caught from raw evidence** — the
  claimed Cisco exit fails against EDGAR/announcement negative-result searches
  (negative results are first-class claims with the search URL as source), and the
  Stripe-tenure/DataLoom-founding overlap is derived from dated talks — and the memo
  opens with them, before the recommendation.
- **A no-LLM validator** rejects any memo sentence or debate turn citing a claim id
  that doesn't exist, and flags uncited quantitative sentences; an LLM critic gets
  exactly one revision round. Grounding is structural, not aspirational.

## Investment Utility & Execution (30%)

- Three fixtures, three different actionable decisions: **invest $100K conditional
  on incorporation** (Tracewell) · **pass, revisit after two named reference calls**
  (Corevance) · **invest $100K conditional on one customer reference call**
  (Parcelmind). Each memo leads with the decision, the claims it turns on, and an
  observable "what would change our mind".
- **Thesis Engine is configurable and consequential**: the Series-A low-risk lens
  kills Tracewell at first-pass, halves Parcelmind's market axis, and re-frames
  Corevance — same data, different fund, different answer. Investors can author a
  new thesis in the UI.
- **Latency instrumented per stage** (signal → screen → extract → adjudicate →
  debate → synthesize); the live run completes a full decision in under a minute,
  and every demo founder shows its strip.
- Gaps render the brief's own words ("Cap table: not disclosed") — enforced by a
  digit-free mechanical gap renderer, tested. No output path can fabricate a value.

## User Experience and Design (15%)

- Five screens that mirror the pipeline itself: **Sourcing** (channel yields,
  ranked feed, Activate, apply form) → **Screening** (three unblended axes with
  trends, kill log) → **Diligence** (claim ledger, adjudication transcripts,
  validator card) → **Memo & Decision** (recommendation first, gap badges, latency
  strip) → **Thesis & Query**.
- The signature interaction: **click any claim citation** → the trace panel walks
  claim → evidence snippet → raw signal (dated, linked) → *how trust was set*,
  including the rubric value struck through where the adjudication judge overrode
  it, with the full prosecutor/defender transcript one click deeper. Agentic
  Traceability as the UI's spine, not a feature toggle.
- One trust-tier color language everywhere; light/dark; no component library.

## Stretch goals

1. **Agentic Traceability — built** (the trace panel + adjudication transcripts above).
2. **Self-Correction Loop — built and visible**: mechanical validator + critic
   revision + per-claim adversarial adjudication with negative-result external checks.
3. **Sourcing & Network Intelligence — partial**: per-channel funnel yields
   (signals → resolved → screened) with an explicitly-labeled heuristic suggestion
   for the underexplored channel; outcome-learning omitted honestly (no funded-deal
   outcomes exist to learn from — faking them would violate the no-fabrication rule).

## Honesty notes (what we did NOT do)

- No LinkedIn scraping (test-enforced). LinkedIn-grade signal enters only via
  founder-supplied channels.
- Signal/Coverage numbers are computed by the scorer, not copied from our design
  docs — they land near, not on, the hand-written targets.
- Replay latencies read ~0s (cache); the recorded live segment shows real timings.
