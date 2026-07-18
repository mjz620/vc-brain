# VC Brain — Product Spec & Execution Plan

Solo build. Aligned to the Maschmeyer Group challenge brief (6th Global AI Hackathon).
Scoring targets: Data Architecture 30% · Investment Utility 30% · Analysis & Trust 25% · UX 15%.

---

## 1. Positioning

One sentence: **an evidence-first sourcing and diligence engine that finds founders before they fundraise, scores what is verifiable rather than who is connected, and produces a gap-honest $100K memo in minutes.**

Three claims the demo must prove:

1. The system *discovers* a fundable founder from public signals alone (sourcing, cold-start).
2. Every sentence in the memo traces to a typed, source-tagged claim with a per-claim Trust Score; contradictions and gaps are surfaced, never papered over.
3. A configurable thesis changes what the system recommends — same data, different fund, different answer.

Anti-goals (from the brief, verbatim or near): no downstream stages (portfolio, follow-on, fund ops, exit), no padding in memos, no single blended score across the three axes, no fabricated financials.

---

## 2. Architecture

Five stages over three layers, per the brief's pipeline.

```
OUTBOUND SCANNER ─┐
                  ├─► MEMORY ─► SCREENING (3-axis) ─► DILIGENCE (claim ledger) ─► DECISION (memo + rec)
INBOUND (deck+name)┘                                                                    │
        ▲                                                                               │
        └────────────────── Activate (outreach draft) ◄── high-score outbound ──────────┘
```

### 2.1 Memory layer — the data foundation

SQLite (single file, zero ops). Three tables:

- **founders** — canonical person records. Fields: id, name, aliases, entity_keys (github handle, HN username, arxiv author id, domain), founder_score (JSON: dimensions + coverage + history), first_seen, last_updated.
- **signals** — raw ingested events, append-only, nothing discarded. Fields: id, founder_id (nullable until resolved), source (github|hn|arxiv|producthunt|deck|web|manual), source_url, content, observed_at, ingested_at, dedup_hash.
- **claims** — the ledger (schema §4). Every claim references ≥1 signal.

Dedup: hash on (source, source_url, normalized content). Entity resolution: a signal attaches to a founder only on co-occurrence of ≥2 entity keys (name + repo, name + company, handle + domain). Unresolved signals stay in the pool — logged, not dropped. "Nothing discarded" is a brief requirement; the append-only signals table *is* the compliance story.

Founder Score persistence: score history is a list of (timestamp, score, trigger) tuples on the founder record. Re-running the pipeline appends, never overwrites → trend over time falls out for free, which the brief explicitly asks for ("surfaces the trend over time, not just the latest snapshot").

### 2.2 Sourcing — build deepest, demo first

**Outbound scanner** (the differentiator; brief says least commercial competition):

- **GitHub** (REST API, no auth needed at demo rate): recently-created repos in the thesis sector's topics with fast star velocity; solo or duo maintainers; commit cadence over trailing 6 weeks. Velocity and consistency, not totals — this is the cold-start instrument.
- **Hacker News** (Algolia API, free, no auth): Show HN posts in sector; extract author, product, engagement.
- **arXiv** (free API): recent papers in sector where an author's affiliation is non-corporate or the paper links a repo — the "paper worth a phone call" case from the brief.
- Optional if time: ProductHunt launches (scrape-free via their API), Devpost hackathon winners.

Each source adapter is ~40 lines: fetch → normalize to signal → ingest. Scanner output is *scored through the same pipeline as inbound* (brief requirement: converge into one funnel).

**Activate:** for candidates crossing the conviction threshold, generate a short outreach draft citing the specific signal that triggered it ("saw your Show HN on X; the retention mechanics in your README caught our screen"). Cheap to build, directly demos the brief's "cold outreach, not cold investment."

**Inbound:** deck (PDF) + company name. Deck → per-page text extraction → claims tagged `source_type=deck`. No extra fields — the brief penalizes over-collecting.

### 2.3 Screening — 3 axes, never averaged

Per opportunity, three independent scores, each with a trend arrow (improving/declining/stable, computed from score history where it exists, else "new"):

- **Founder axis** — takes the persistent Founder Score as *one input* (brief FAQ 6 insists these are distinct), plus opportunity-specific fit.
- **Market axis** — bullish/neutral/bear + sizing claims.
- **Idea-vs-Market axis** — does the idea survive as-is, or is this a bet on the team's ability to pivot. Operationalize as: (competitive density from the competition worker) × (differentiation strength of verified claims) with an explicit one-line rationale.

First-pass screen: a single cheap model call that kills clearly non-viable inbound before full analysis (brief §4). Log the kill reason.

### 2.4 Diligence — claim ledger + Trust Score

Schema (Pydantic, structured output on every worker call):

```python
class Claim(BaseModel):
    id: str                    # "team-03"
    axis: Literal["founder","market","idea","traction","risk"]
    text: str
    stance: Literal["supports","contradicts","neutral"]
    evidence: str              # snippet
    source_url: str
    source_type: Literal["deck","web","github","hn","arxiv","inferred","unavailable"]
    corroboration: Literal["self_reported","single_source","corroborated","contradicted"]
    trust: float               # 0–1, rubric-anchored
    observed_at: str | None
```

Trust Score = f(corroboration tier, source attestation strength, recency). Self-reported caps trust at 0.6. `contradicted` claims are *promoted to the top of the memo*, not buried — the brief scores contradiction-flagging directly.

Workers (async, parallel): founder (deepest — timeline reconstruction, Form D lookup, disambiguation drop-log), market, competition, traction. Red-team runs as a second pass over the assembled ledger hunting kill criteria and writing DD-log open items.

Synthesizer writes the memo under the hard constraint: every sentence cites ≥1 claim id. Mechanical regex validator (no LLM) → LLM critic verifies semantic support → max 1 revision round.

### 2.5 Decision — memo + recommendation

**Required sections only** (brief appendix): Company snapshot · Investment hypotheses · SWOT · Problem & product · Traction & KPIs. Plus two cheap adds that score: **DD log** (the ledger rendered: what was checked, what's open, what would close each gap) and a top-line **Recommendation** block (invest/pass, $100K, the 2–3 claims the decision turns on, per-axis scores side by side — never blended).

Gap rendering: any section lacking claims renders the brief's own language — "Cap table: not disclosed." This is scored *positively*; treat it as a feature with UI weight, not an apology.

**Thesis Engine:** a YAML/JSON config — sectors, stage, geography, check size, ownership target, risk appetite. Applied twice: as a filter on the sourcing scanner and as a scoring lens in screening (each axis rationale must reference the thesis). Demo two configs against the same founder pool to prove configurability (brief FAQ 15).

**Multi-attribute query:** one model call parses NL → structured filter over Memory + a rank pass. "Technical founder, Berlin, AI infra, enterprise traction, no prior VC backing" resolves in one pass. ~1 hour of work, directly named in the brief as MVP item 3.

### 2.6 Instrumentation — free points

The Investment Utility criterion (30%) explicitly credits "instrumenting how fast and reliably an opportunity moves from first signal to decision." Log timestamps at every stage transition; render a per-opportunity latency strip (signal → screen → memo: 4m 32s) on the dashboard. Trivial to build, directly named in a 30% criterion.

---

## 3. Cold-start method (explicit, per FAQ 10–11)

Principle: **score observable execution velocity, not accumulated pedigree.** For a founder with no funding history, no network, thin GitHub:

1. **Velocity over volume** — commit cadence, ship frequency, iteration speed over the trailing 6–12 weeks. A 6-week-old repo with daily commits and three releases outscores a 5-year-old stale one.
2. **Public footprint as evidence** — writing (blog, HN comments in-domain), talks, course projects, hackathon submissions. Anything dated and attributable becomes a claim.
3. **Coverage stays honest** — cold-start founders get a *low-coverage* flag, not a low score. The UI renders "Signal 7.1 · Coverage 22%" differently from "Signal 4.0 · Coverage 85%." The system's recommendation for low-coverage/high-signal: activate (outreach, request materials), not reject.
4. **Self-reported cap still applies** — but the cap is per-dimension, so a cold-start founder with verifiable shipped work can still score high on execution.

One demo founder must be a synthetic cold-start profile (student, no funding, 6 weeks of public building) that the outbound scanner surfaces and scores above a credential-heavy but stale synthetic profile. That contrast is the equitable-allocation thesis of the whole brief made visible in one screen.

---

## 4. Demo data plan

Per the brief, synthetic data with seeded contradictions is explicitly sanctioned.

- **Founder A (cold-start):** synthetic student profile + real-ish GitHub-style signal history. Surfaced by outbound scanner.
- **Founder B (credentialed, contradicted):** synthetic profile with 2 seeded contradictions (claimed exit vs. no Form D; tenure overlap). The contradiction-flagging demo.
- **Founder C (inbound):** fictional pitch deck (write it in an hour; include one fabricated-looking metric for the red-team to catch, and omit the cap table so the gap-flagging renders).

Deterministic demo: `--replay` on all three. Live run recorded once during filming.

---

## 5. Execution plan

Hours renumbered from now (T0). Compress by cutting from the bottom of each block, not by skipping blocks.

| Block | Hours | Deliverable |
|---|---|---|
| 0. Target artifacts | T0–T1 | Hand-write Founder B's memo + the dashboard sketch. Write the 3 synthetic profiles + fictional deck outline. |
| 1. Memory + schemas | T1–T2.5 | SQLite tables, Claim/Founder models, dedup hash, ingest fn, `--replay` scaffolding |
| 2. Outbound scanner | T2.5–5 | GitHub + HN adapters end-to-end into Memory; arXiv if pacing well. Entity resolution w/ drop-log |
| 3. Screening | T5–6.5 | First-pass filter, 3-axis scoring w/ anchored rubrics, thesis config applied |
| 4. Diligence | T6.5–9 | Workers (founder deepest), ledger assembly, red-team pass, synthesizer + mechanical validator + critic |
| 5. Decision + memo | T9–10.5 | 5 required sections + DD log + rec block; gap rendering; latency instrumentation |
| 6. Frontend | T10.5–13 | Dashboard (ranked list, trend arrows, latency strip), memo view w/ click-to-evidence, thesis config panel, NL query box |
| 7. **Feature freeze** | T13 | Whatever is broken gets cut, not fixed |
| 8. Demo + video | T13–16 | Cache 3 founder runs, record live run once, then scripted takes |
| 9. Submission | T16–18 | Write-up (mirror rubric headings), repo cleanup, buffer |

Cut order if behind: arXiv adapter → NL query → activate/outreach → critic loop (keep mechanical validator) → Founder C inbound path (demo outbound-only).

Do-not-cut list: outbound scanner, claim ledger + Trust Score, cold-start contrast demo, gap rendering, per-axis (unblended) scores, latency strip.

---

## 6. Demo script skeleton (3 min)

1. **0:00–0:20** — Thesis config on screen. "This fund wants pre-seed AI infra, $100K checks. Watch it find someone who hasn't started raising."
2. **0:20–1:00** — Outbound scanner surfaces Founder A (cold-start). Signal/coverage split visible. System drafts activation outreach citing the triggering signal.
3. **1:00–1:50** — Founder B memo. Click a sentence → evidence expands. The two seeded contradictions flagged at top. Cap table section reads "not disclosed."
4. **1:50–2:20** — 3-axis view, not averaged: Founder strong, Market bear, Idea-vs-Market = pivot bet. The disagreement *is* the display.
5. **2:20–2:45** — Latency strip: first signal → decision in minutes. Swap thesis config → recommendation changes.
6. **2:45–3:00** — Eval numbers: claim-verification accuracy by corroboration tier, score stability across reruns. Close on the equitable-allocation line.

---

## 7. Eval (report these numbers in the write-up)

1. **Claim accuracy by tier** — 30 sampled claims hand-verified against cited sources; report % supported per corroboration tier. If corroborated ≫ self_reported, that validates the tiering.
2. **Score stability** — each founder scored 3–5×; report spread. Anchored rubrics + per-dimension calls keep this tight.
3. **Sensitivity** — remove one corroborating source from Founder B; show trust drops and the affected memo sentence flips to flagged.
4. **Latency** — median signal→decision time across the three demo founders.
