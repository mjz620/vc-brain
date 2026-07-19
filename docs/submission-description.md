# FirstSignal — submission form answers

Paste each section into the matching field. Every number was read from the live
database on 2026-07-19 and is reproducible from the repo.

---

## Short Description

FirstSignal is an evidence-first venture intelligence platform that finds exceptional founders before they start fundraising, then verifies every claim about them against external evidence. It scans seven public builder ecosystems, resolves signals into persistent founder identities, and runs an adversarial diligence pipeline that produces an investment memo where every number carries a trust score and a link to its source.

---

## 1. Problem & Challenge

Venture capital has a discovery problem and a verification problem, and they compound.

**Discovery:** capital flows through networks, not merit. A fund sees the founders who reach its inbox — warm intros, demo days, the people already pitching. Builders shipping real work outside that network stay invisible until someone else funds them, and by the time a company is legible to the market, the entry price reflects it.

**Verification:** a deck is, by construction, the founder's most favourable account of themselves. Corroborating it takes weeks, so under time pressure the skipped check is the one that matters most — does the claimed history survive contact with the public record?

Generic AI tooling widens the gap rather than closing it. A model that summarises a deck fluently produces a document that *reads* like diligence while inheriting every unverified claim in the source, with no way to tell which sentences are load-bearing.

The hard problem is not summarisation. It is knowing what you actually know.

---

## 2. Target Audience

**Primary: early-stage investment teams** (pre-seed and seed) at funds small enough that the partner is also the analyst. They feel both halves of the problem — no proprietary deal flow, no research team to verify what arrives — and have to reach a defensible invest/pass call on a Tuesday.

**Secondary:**

- **Platform and sourcing leads**, who need to answer "which channels actually produce quality for us" with evidence rather than intuition.
- **Investment committees**, who receive the memo. The audience for the output is not the person who ran the analysis — it is the people who must interrogate it.
- **Founders outside the network**, indirectly: a system that scores evidence rather than pedigree is one where a builder with no warm intro can surface.

---

## 3. Solution & Core Features

FirstSignal runs the full funnel — **Sourcing → Screening → Diligence → Decision** — as one evidence-preserving pipeline.

**Outbound sourcing.** Seven adapters ingest from GitHub, Hacker News, arXiv, Product Hunt, YC cohorts, a company launch tracker that surfaces startups the week they debut, and open-web search. Inbound applications enter the same funnel via pasted text or an uploaded PDF deck.

**Identity resolution.** A signal links to a founder only on **two co-occurring identity keys**. Single-key matches are refused, and platform domains and their subdomains can never act as identity. Unresolved signals go to a visible drop log — 209 entries — rather than being silently merged.

**Persistent Founder Score, separate from Coverage.** A Signal score is derived mechanically from execution velocity, community pull, source breadth, integrity and verified depth, with append-only history. **Coverage is reported separately and never blended in**, so a sparse record reads as *uncertain*, not *weak*.

**Independent screening.** Founder, Market and Idea-vs-Market are scored as three separate axes through a configurable thesis lens, never averaged into one number.

**Adversarial diligence.** Extraction workers build a claim ledger; contested claims go to prosecutor, defender and judge agents whose verdict can override the base trust rubric. Every claim carries a tier — self-reported, single-source, corroborated, contradicted — and contradictions lead the memo rather than being buried.

**Decision artifact.** An invest/pass/conditional recommendation with the claims it turns on, an explicit "what would change our mind," a gap list, per-stage latency, grounded Q&A over the ledger, and a PDF export.

**Sourcing graph.** Channels, startups, founders and early investors in one graph, joining curated public outcome references with live pipeline yield — and feeding the fund's own decisions back to the channel that sourced each founder.

---

## 4. Unique Selling Proposition (USP)

**FirstSignal finds mispriced founders, proves why, and gets sharper every time the fund decides.**

### It finds the deals the market hasn't priced

Evidence *volume* and founder *quality* are different variables, and conflating them is how funds overpay. Corevance is the deal everyone can see: polished application, **92% coverage — and Signal 4.6**, because its acquisition claim has no public record and its CEO timeline overlaps the same founder's employment elsewhere. Tracewell never applied to anyone: **46% coverage, Signal 8.4**, found outbound from shipping velocity and organic adoption, everything verifiable checking out.

Blend those into one score and the contradicted company outranks the real one. FirstSignal ranks them correctly, and that gap *is* the alpha — pedigree is already priced; verified execution outside the network is not.

### The sourcing graph is an intelligence asset, not a visualisation

It joins curated public outcome references with this deployment's live yield, and closes the loop by feeding the fund's own invest/pass/conditional decisions back to the channel that sourced each founder.

That produces conclusions a partner can act on this week: **GitHub yields a median founder Signal of 8.3 against YC's 4.0**; **Launch Tracker resolves at 1.0** — 10 of 10 signals, zero drops — because its entries carry both a domain and a founder name. The graph also names the high-potential channels the fund is *not* scanning. No competitor can copy this, because no competitor has that funnel.

### Credibility is enforced in code, not asserted in prose

Every number carries a claim ID, a trust tier and a source link. A mechanical validator rejects citations to claim IDs that don't exist, and an integrity gate counts contradictions in code rather than trusting a model's tally — both run outside the model, so a prompt cannot argue with them. The methodology page is generated from the actual scoring constants, so the explanation cannot drift from the implementation.

That is what makes conviction bankable: an IC can interrogate a FirstSignal memo line by line, and each line survives or falls on its own evidence.

### It compounds

Three flywheels run at once. **Evidence:** append-only memory makes the verified claim ledger a proprietary asset that only grows. **Sourcing:** every decision sharpens which channels get scanned next. **Coverage:** adapters share one interface, so each new source multiplies against every founder already in memory.

A fund running FirstSignal for six months has something a fund starting today cannot buy — its own resolved founder graph, its own decision history, and channel rankings earned from its own outcomes.

---

## 5. Implementation & Technology

**Stack:** React + TypeScript (Vite), FastAPI, Supabase PostgreSQL in deployment with SQLite locally, Tavily for external evidence, OpenAI/Anthropic for the agent layer, ReportLab for PDF export. 74 automated tests.

**Memory.** An append-only signals table enforced by a database trigger, so provenance cannot be rewritten after the fact. Content-hash deduplication rejects duplicates. Entity resolution is its own ledger, keeping raw signals independent of interpretation. Claims carry a `subject`, so a multi-founder company attributes evidence to the right person instead of collapsing the team into one.

**Ingestion.** Seven adapters behind a common interface, each returning normalised signals plus candidate entity keys. Every external fetch is cached on first call; runs replay deterministically, with a strict mode that fails on a miss rather than silently going live.

**Intelligence.** Extraction workers per axis emit claim drafts under enforced schemas. Contested claims route to three-agent adversarial adjudication (prosecutor / defender / judge). A separate bull/bear debate argues the investment case before a synthesizer writes the memo.

**Deterministic guardrails.** A validator rejects citations to non-existent claim IDs and flags uncited quantitative assertions. The integrity gate's input — contradicted founder claims — is counted in code, so a pass citing contradictions the ledger doesn't hold is rejected by construction.

**Instrumentation.** Per-stage wall-clock timing is persisted for every run, so signal-to-decision latency is measured rather than estimated.

**Current state:** 285 signals, 116 resolved founders, 141 evidence-linked claims, 209 logged drops, 9 first-pass kills.

---

## 6. Results & Impact

**Opposite conclusions on two companies, for the right reasons.** Corevance — a polished inbound application at 92% coverage — is a **pass**: its deck claims an acquisition with no public record and a CEO tenure overlapping the same founder's employment elsewhere. Tracewell, which never applied and was found outbound, gets **invest, $100,000** at Signal 8.4 with 46% coverage. Higher coverage did not win; verifiable evidence did.

**It works on a real company, not just fixtures.** Skillset (skillset.co) was run end to end on live APIs. The system attributed each co-founder's record to the right person, refused weakly-sourced credential claims, and pulled a corroborated ITSM market size of **$9.58B by 2035 at trust 0.85** — while rendering revenue, customer count and round size as flagged gaps, because none are public.

**Sourcing yield is measurable.** Launch Tracker resolves at **1.0** (10 of 10, zero drops); YC at 0.97, GitHub at 0.54, arXiv at 0.07. GitHub produces the highest-quality founders here — **median Signal 8.3 against YC's 4.0** — an actionable sourcing conclusion drawn from the fund's own pipeline rather than intuition.

**Speed.** Inbound deck to a cited, contradiction-first memo with a recommendation runs in a single session, per-stage latency recorded — against the weeks the same verification takes by hand.

**Precision is the differentiator, and it is measurable.** Where a criterion is backed by ingested data, FirstSignal evaluates it and states the population it evaluated over — geography resolves across 38 founders and reports that denominator explicitly. Where no source backs a criterion, the system says so rather than generating a plausible answer. Nothing in the memo is decorative, so an IC spends its time on the decision instead of auditing the analysis.

**Where it goes next.** The architecture is additive: each new adapter multiplies against every founder already in memory. Funding-history and richer geography sources are next, widening compound query coverage. The decision-feedback loop is live today; as decision volume grows it turns channel rankings from quality-weighted into outcome-weighted — the compounding advantage no competitor can shortcut. Commercial, legal and cap-table diligence are the natural expansion from a copilot that compresses the funnel toward one that closes it.
