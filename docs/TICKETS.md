# TICKETS — Future Extensions Backlog

Deferred work to pick up **after** the core Sourcing → Screening → Diligence → Decision pipeline is built
and the demo is deterministic. Nothing here is in scope for the hackathon blocks (spec §5); this is the
"down the line" list so we don't lose the ideas.

Status legend: `backlog` (captured, not started) · `next` (first thing after core) · `parked` (needs a
decision first).

---

## T-01 · Real slide-deck ingestion into the pipeline · `next`

**What:** Ingest *actual* pitch-deck files (PDF/PPTX) as a first-class inbound source, replacing the
hand-written `deck-summary.txt` fixtures. Deck → per-page/slide extraction → `source_type=deck` signals →
claims, wired into the same funnel as outbound (spec §2.2 inbound path).

**Why now-ish:** The core build uses text-summary decks so Block 4 workers have something to cite
deterministically. The brief's minimum inbound input is "deck + company name" — handling a real binary
deck is the natural first extension and makes the inbound demo genuinely end-to-end.

**Sketch:**
- PDF text: Claude PDF document input (base64 `document` block) or a local extractor; PPTX via `python-pptx`.
- One slide = one signal (`source_url` = `file://<deck>#slide-N`, `observed_at` = submission date).
- Vision pass on slides that are charts/screenshots (metrics live in images) — Opus high-res vision.
- Keep the fixture decks as golden replay inputs; add 1–2 real anonymized decks as live-run material.
- **Guardrail:** extracted deck numbers are `self_reported` claims (trust capped 0.6) until externally
  corroborated — same rule as the current fixtures. No silent trust inflation from "it was in the deck."

---

## T-02 · Broader info ingestion (heterogeneous sources) · `backlog`

**What:** Expand ingestion beyond GitHub/HN/arXiv/deck to more of the brief's named sources —
ProductHunt launches, Devpost hackathon winners, patents (real USPTO/Google Patents), company websites,
and dated public writing (blogs, talk abstracts). Each is a ~40-line adapter → Signal → same funnel.

**Why:** Data Architecture is 30% and rewards ingestion *breadth + quality*, especially for the
cold-start case. More dated, attributable footprint = more first-class claims for thin-record founders.

**Sketch:** one adapter per source, all writing through the existing `ingest_signal` + entity resolution;
cache every live response in the replay store. Add a per-source "signal yield" stat to the sourcing-graph
view (see T-03).

---

## T-08 · Expand sourcing corpus + live-time updates · `next`

**What:** Two related pushes on the data layer (Data Architecture is 30%, the highest-weight axis).

1. **Broaden the sourcing corpus** — go well beyond GitHub/HN/arXiv. Add ProductHunt, Devpost, real
   patents (USPTO/Google Patents), accelerator cohorts, company sites, dated public writing, and
   founder-supplied profiles (T-07). Also add a **live external-verification worker** for the *diligence*
   step so the negative-result checks (EDGAR, acquisition records) are fetched at diligence time rather
   than seeded as fixtures. (Overlaps + extends T-02; this is the priority framing.)

2. **Live-time updates** — move from one-shot scans to *continuous* refresh: re-scan on a schedule /
   webhook, ingest new signals as they appear, and let the append-only Founder Score history update in
   place so the trend arrows reflect real movement over time (not just re-runs). Watch specific founders;
   re-screen when a new signal crosses a threshold (the brief's "signals crossing a conviction threshold
   on their own"). Requires: a scheduler, per-source incremental cursors, and cache-invalidation policy
   so live updates don't silently break `--replay` determinism (keep a frozen demo snapshot separate
   from the live-updating store).

**Why:** richer + fresher data is the core differentiator the brief rewards, and live-time updating is
what turns this from a batch tool into the "living intelligence network" framing.

---

## T-03 · Sourcing-graph / network intelligence (stretch goal 3) · `backlog`

**What:** Model the sourcing graph — programs, institutions, channels through which founders become
visible — and track which channels historically produce the strongest opportunities; suggest
underexplored channels; feed funded-deal outcomes back so it learns quality, not just volume.

**Why:** Named stretch goal in the brief; directly extends the sourcing layer (the highest-weight area).

---

## T-04 · Confidence intervals on soft-skill assessments (research area 1) · `parked`

**What:** Prediction intervals around soft assessments (resilience, founder-market fit) rather than point
Trust Scores. Framed as genuinely open in the brief.

**Why parked:** Needs a methodology decision and eval design before any code; only worth it once the
deterministic Trust Score tiering is validated (spec §7 eval #1).

---

## T-05 · Persist runs / multi-fund workspace · `backlog`

**What:** Beyond the single demo DB — persist multiple pipeline runs, multiple thesis configs side by
side, and per-fund views. Currently one `vc_brain.db`; the schema already supports append-only history, so
this is mostly UI + a `run_id` dimension.

---

## T-07 · LinkedIn-grade signal via compliant channels (NOT scraping) · `backlog`

**What:** Capture LinkedIn-type signal (employment history, tenure, education, job changes) — high-signal,
but **never** by scraping. Ingest it through channels that don't violate ToS:
- **Founder-supplied:** pasted profile text or a LinkedIn data export the applicant uploads with their deck.
- **Official API / partner data** if/when a partnership exists.
- **Founder-listed URL as a pointer**, used only to know *what to verify* against dated primary sources.

**Why not scraping (settled):** it's a spec guardrail (§2.2) + a Block 2 gate; ToS-prohibited and
bot-walled (*hiQ v. LinkedIn*); and it's the pedigree/network surface the equitable-allocation thesis
corrects against (brief FAQ 10). A test already asserts no `linkedin` scraper module exists.

**How it fits the existing model:** LinkedIn-derived facts enter as `source_type` deck/web claims with
`corroboration=self_reported` (trust capped 0.6), then get cross-verified against talks/patents/Form D —
exactly the Corevance contradiction demo (Stripe tenure vs. DataLoom founding overlap). No new trust path;
just a new *input* channel behind founder consent.

---

## T-06 · Activate / outreach send path · `backlog`

**What:** The spec generates the outreach draft (cold outreach, not cold investment). A later extension
actually *sends* (email/DM) behind a human-approval gate, and tracks whether it converts to an application
— closing the outbound → inbound loop the brief describes.

**Why deferred:** Outbound-scanner + draft generation is in scope; the send path is an external side
effect that needs approval gating and isn't needed to demo the loop.
