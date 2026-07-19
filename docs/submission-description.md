# FirstSignal — submission form answers

Paste each section into the matching field. Every number below was read from the
live database on 2026-07-19 and is reproducible from the repo.

---

## Short Description

FirstSignal is an evidence-first venture intelligence platform that discovers exceptional founders before they start fundraising, then verifies every claim about them against external evidence. It scans six public builder ecosystems, resolves signals into persistent founder identities, and runs an adversarial diligence pipeline that produces an investment memo where every number carries a trust score and a link to its source.

---

## 1. Problem & Challenge

Venture capital has a discovery problem and a verification problem, and they compound each other.

**Discovery:** capital flows through networks, not merit. A fund sees the founders who reach its inbox — warm intros, demo days, the people already pitching. Exceptional builders shipping real work outside that network are invisible until someone else funds them. By the time a company is legible to the market, the entry price reflects it.

**Verification:** the diligence that would justify a fast decision takes weeks. Analysts read a deck that is, by construction, the founder's most favourable account of themselves, then spend days trying to corroborate it. Under time pressure the check that gets skipped is precisely the one that matters — does the claimed history survive contact with the public record?

The result is a system that is simultaneously too slow to act on conviction and too fast to verify. Generic AI tooling makes this worse rather than better: a model that summarises a pitch deck fluently produces a document that *reads* like diligence while inheriting every unverified claim in the source, with no way for a reader to tell which sentences are load-bearing.

The hard problem is not summarisation. It is knowing what you actually know, and being honest about the rest.

---

## 2. Target Audience

**Primary: early-stage investment teams** (pre-seed and seed) at funds small enough that the partner is also the analyst. They are the ones who feel both halves of the problem — no proprietary deal flow engine, and no research team to verify what arrives. FirstSignal is built for the person who has to reach a defensible invest/pass call on a Tuesday.

**Secondary:**

- **Platform and sourcing leads** at larger funds, who need to answer "which channels actually produce quality for us" with evidence rather than intuition.
- **Investment committees**, who receive the exported memo. The audience for the output is not the person who ran the analysis — it is the people who must interrogate it, which is why every claim is traceable rather than merely stated.
- **Founders outside the network**, indirectly. A system that scores evidence rather than pedigree is one where a builder with no warm intro can still surface.

---

## 3. Solution & Core Features

FirstSignal runs the full funnel — **Sourcing → Screening → Diligence → Decision** — as one evidence-preserving pipeline.

**Outbound sourcing.** Six adapters ingest from GitHub, Hacker News, arXiv, Product Hunt, YC cohorts, and a company launch tracker that surfaces startups the week they debut. Signals are append-only and content-hash deduplicated. Inbound applications enter the same funnel via pasted text or an uploaded PDF deck.

**Identity resolution.** A signal links to a founder only on **two co-occurring identity keys**. Single-key matches are refused, and infrastructure domains (github.com, linkedin.com) are blacklisted so they can never act as identity. Unresolved signals go to a visible drop log — currently 167 entries — rather than being silently merged or discarded.

**Persistent Founder Score, separate from Coverage.** A founder carries a Signal score derived mechanically from execution velocity, community pull, source breadth, integrity, and verified depth — with an append-only history. **Coverage is reported separately and never blended in**, so a sparse record reads as *uncertain*, not *weak*.

**Independent screening.** Founder, Market, and Idea-vs-Market are scored as three separate axes through a configurable thesis lens. They are never averaged into one reassuring number.

**Adversarial diligence.** Extraction workers build a claim ledger; contested claims go to prosecutor, defender, and judge agents whose adjudication can override the base trust rubric. Each claim carries a trust tier — self-reported, single-source, corroborated, contradicted — and contradictions are surfaced *first* in the memo, not buried.

**Decision artifact.** An invest/pass/conditional recommendation with the specific claims it turns on, an explicit "what would change our mind," a gap list, per-stage latency, grounded Q&A over the ledger, and a PDF export.

**Sourcing graph.** Channels, startups, founders, and early investors in one force-directed graph, joining curated public outcome references with this deployment's live pipeline yield — and with the fund's own decisions fed back to the channel that sourced each founder.

---

## 4. Unique Selling Proposition (USP)

**FirstSignal finds mispriced founders, proves why, and gets sharper every time the fund decides.**

### It finds the deals the market hasn't priced yet

The core insight is that evidence *volume* and founder *quality* are different variables, and conflating them is how funds systematically overpay. Corevance is the deal everyone can see: a polished application, **92% coverage — and Signal 4.6**, because its acquisition claim has no public record and its CEO timeline overlaps the same founder's employment elsewhere. Tracewell never applied to anyone: **46% coverage, Signal 8.4**, discovered outbound from shipping velocity and organic adoption, and everything verifiable checks out.

Any system that blends those into a single score ranks the contradicted company above the real one. FirstSignal ranks them correctly — and that gap *is* the alpha. Pedigree is already priced; verified execution outside the network is not.

### The sourcing graph is an intelligence asset, not a visualisation

Channels, startups, founders, and early investors sit in one graph that joins curated public outcome references with this deployment's live pipeline yield — and closes the loop by feeding the fund's own invest/pass/conditional decisions back to the channel that sourced each founder.

That produces sourcing conclusions a partner can act on this week: **GitHub yields a median founder Signal of 8.3 against YC's 4.0** in this pipeline. **Launch Tracker resolves at 1.0** — 10 of 10 signals, zero drops — because its entries carry both a domain and a founder name. The graph also names the high-potential channels the fund is *not* scanning yet. This is proprietary sourcing intelligence derived from the fund's own funnel, and no competitor can copy it because no competitor has that funnel.

### Credibility is enforced in code, not asserted in prose

Every number in every memo carries a claim ID, a trust tier, and a link to its source. A mechanical validator — code, not a prompt instruction — rejects citations to claim IDs that don't exist. Contradictions are surfaced *first* in the memo, not buried in an appendix. The methodology page is generated from the actual scoring constants, so the explanation cannot drift from the implementation. Every run is replayable from cache, so any result can be reproduced on demand.

This is what makes conviction bankable: an investment committee can interrogate a FirstSignal memo line by line, and each line survives or falls on its own evidence. A fluent summary of a pitch deck cannot do that — it inherits every unverified claim in the source with no way to tell which sentences are load-bearing.

### It compounds

Three flywheels run at once. **Evidence:** memory is append-only, so the fund's verified claim ledger becomes a proprietary asset that only grows. **Sourcing:** every decision recorded sharpens which channels get scanned next. **Coverage:** adapters sit behind a common interface, so each new source multiplies against every founder already in memory rather than starting over.

A fund running FirstSignal for six months has something structurally unavailable to one starting today — its own resolved founder graph, its own decision history, and channel rankings earned from its own outcomes.

---

## 5. Implementation & Technology

**Stack:** React + TypeScript (Vite) frontend, FastAPI backend, Supabase PostgreSQL in deployment with SQLite locally, Tavily for external evidence retrieval, OpenAI/Anthropic for the agent layer, ReportLab for PDF export. 65 automated tests.

**Memory layer.** An append-only signals table protected by a database trigger — signals are immutable once written, so provenance cannot be rewritten after the fact. Content-hash deduplication rejects re-ingested duplicates. Entity resolution is its own ledger, keeping raw signals independent of interpretation. Claims carry a `subject` field so a multi-founder company attributes evidence to the correct individual rather than collapsing the team into one person.

**Ingestion.** Six modular source adapters behind a common interface, each returning normalised signals plus candidate entity keys. Every external fetch is cached on first call; runs replay from cache with a strict mode that fails on a miss rather than silently going live.

**Intelligence layer.** Extraction workers per axis produce structured claim drafts under enforced schemas. Contested claims route to a three-agent adversarial adjudication (prosecutor / defender / judge). A separate debate stage argues the investment case bull and bear before a synthesizer writes the memo.

**Deterministic guardrails.** A mechanical validator rejects citations to claim IDs that do not exist and flags uncited quantitative assertions. This runs outside the model — it is code, not a prompt instruction, so it cannot be argued with.

**Instrumentation.** Per-stage wall-clock timing is persisted for every run, so signal-to-decision latency is measured rather than estimated.

**Current state:** 278 signals, 114 resolved founders, 140 evidence-linked claims, 167 logged drops, 9 first-pass kills.

---

## 6. Results & Impact

**The system reaches opposite conclusions on two companies for the right reasons.** Corevance — a polished inbound application with 92% coverage — is a **pass**: its deck claims an acquisition with no public record and a CEO tenure that overlaps the same founder's employment elsewhere. Tracewell, which never applied and was discovered outbound from shipping velocity and organic adoption, gets a **conditional $100,000 recommendation** at Signal 8.4 with 46% coverage. Higher coverage did not win; verifiable evidence did.

**It works on a real company, not just fixtures.** Skillset (skillset.co) was run end to end on live APIs. The system correctly attributed each co-founder's record to the right person, refused to accept weakly-sourced credential claims, and pulled a corroborated ITSM market size of **$9.58B by 2035 at trust 0.85** — while rendering revenue, customer count, and round size as flagged gaps, because none of those are public.

**Sourcing yield is measurable.** Launch Tracker resolves at **1.0** (10 of 10 signals, zero drops) because its entries carry both a domain and a founder name; YC resolves at 0.97, GitHub at 0.54, arXiv at 0.07. GitHub produces the highest-quality founders in this deployment — **median Signal 8.3 against YC's 4.0** — which is an actionable sourcing conclusion drawn from the fund's own pipeline rather than from intuition.

**Speed.** Inbound deck to a cited, contradiction-first memo with an invest/pass/conditional recommendation runs in a single session, with per-stage latency recorded — against the weeks the same verification takes manually.

**Precision is the differentiator, and it is measurable.** Where a criterion is backed by ingested data, FirstSignal evaluates it and states the population it evaluated over — geography resolves across 38 founders today and reports that denominator explicitly. Where a criterion has no source behind it, the system says so rather than generating a plausible answer. That discipline is exactly why the memo holds up under questioning: nothing in it is decorative, so an investment committee can spend its time on the decision instead of on auditing the analysis.

**Where it goes next.** The architecture is deliberately additive — each new adapter multiplies against every founder already in memory. Funding-history and richer geography sources are next, extending compound query coverage. The decision-feedback loop is built and live today; as decision volume grows it turns channel rankings from quality-weighted into outcome-weighted, which is the compounding advantage no competitor can shortcut. Commercial, legal, and cap-table diligence are the natural expansion from an analyst copilot that compresses the funnel toward one that closes it end to end.
