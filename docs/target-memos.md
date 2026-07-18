# Target Memos — Demo Fixtures

Three synthetic founders, per spec §4. Style follows the Bessemer memos: recommendation first, weaknesses stated plainly, probabilities on outcomes. Every sentence that makes a factual assertion carries a claim ID with its Trust Score and corroboration tier — this is the output format the synthesizer must reproduce.

Notation: `[claim-id · trust · tier]` where tier ∈ self / single / corr (corroborated) / CONTRA (contradicted).

---

# MEMO 1 — Tracewell (Founder A: cold start, sourced outbound)

**To:** IC · **Re:** Tracewell — $100K pre-seed recommendation
**Source of opportunity:** Outbound scanner (GitHub velocity + Show HN), not inbound. Founder has not begun fundraising. [src-01 · 0.95 · corr]

## Recommendation

**Invest $100K on a post-money SAFE, conditional on incorporation.** Signal 7.8 / Coverage 24%. The record is thin because the founder is 21 and nine weeks into public work — not because the work is weak. What exists is verifiable and fast-moving. Outcome view: 45% quiet failure, 40% modest outcome, 15% meaningful company; at $100K, the asymmetry is acceptable and the pre-fundraise entry is the entire point of this system.

**What would change our mind:** two weeks of stalled commit cadence, or evidence the core benchmark results don't replicate [open-03].

## Company snapshot

Tracewell is an open-source evaluation harness for LLM agent pipelines — regression testing for agent behavior the way CI regression-tests code [prod-01 · 0.9 · corr]. Agent deployments fail silently when model or prompt changes shift behavior; teams currently hand-roll checks. The repo is 9 weeks old with 1,420 stars and 40+ external issue filers, suggesting the pain is real and current [trac-01 · 0.9 · corr].

## Investment hypotheses

- **Execution velocity:** 61 consecutive days with commits, 3 tagged releases, median issue response under 8 hours [team-02 · 0.9 · corr]. This cadence is the strongest founder signal available at this stage.
- **Community pull, not push:** #2 Show HN of its day (890 points); 11 of the last 20 merged PRs are external contributors [trac-02 · 0.85 · corr].
- **Wedge → expansion:** open-source harness → hosted eval dashboard → enterprise compliance reporting for agent behavior. Classic infra motion; unproven here [hyp-01 · 0.4 · inferred].

## SWOT

- **S:** verifiable shipping speed [team-02]; organic developer adoption [trac-01, trac-02].
- **W:** solo founder, no commercial experience, not incorporated [team-04 · 0.9 · corr]. No revenue, no pricing tested.
- **O:** agent-eval category is early; no dominant incumbent [mkt-02 · 0.6 · single].
- **R:** LangSmith / Braintrust could absorb the feature [risk-01 · 0.7 · single]; solo-founder key-person risk is total.

## Problem & product

Teams shipping LLM agents cannot tell whether a prompt or model update changed agent behavior until users complain. Tracewell records agent traces, lets developers pin expected behaviors, and fails CI when behavior drifts [prod-01]. Works today with two major agent frameworks [prod-02 · 0.8 · corr — verified against repo examples].

## Traction & KPIs

1,420 GitHub stars, 9 weeks [trac-01 · corr]. ~3,100 weekly package downloads [trac-03 · 0.7 · single — registry stats, single source]. Revenue: none; product is pre-monetization [flag]. Customer count: not applicable at this stage [flag].

**Financials & round structure: not applicable — company not yet incorporated.**
**Cap table: not applicable — will be trivial at formation; condition of investment.**

## Due diligence log

Checked: repo authorship and commit history [team-02]; Show HN authorship matches GitHub identity via linked domain [src-01]; download stats [trac-03]; framework compatibility claims reproduced locally [prod-02].
**Open:** (open-01) founder identity/background beyond public handles — no employment or education claims made, none verified; (open-02) whether any prior collaborators would co-found; (open-03) independent replication of the benchmark table in the README.
**Discarded:** 6 signals failed entity resolution (same-name GitHub accounts) — logged, excluded.

---

# MEMO 2 — Corevance (Founder B: credentialed inbound, contradictions found)

**To:** IC · **Re:** Corevance — pass recommendation
**Source:** Inbound application (deck + name).

## ⚠ Contradictions found (2) — read first

1. **Claimed exit does not appear in the public record.** The deck states DataLoom was "acquired by Cisco, 2021" [team-10 · CONTRA]. No Form D exists for DataLoom's claimed $4M seed [dd-02 · 0.9 · corr — EDGAR search, negative result]; Cisco's 2021 acquisition announcements do not include DataLoom [dd-03 · 0.85 · corr]. Consistent with an unannounced acquihire, which is materially different from the "successful exit" framing.
2. **Timeline overlap.** Founder's profile shows full-time Stripe employment through mid-2020 [team-11 · 0.6 · self]; DataLoom's own materials date founding to March 2019 with the founder as full-time CEO [team-12 · CONTRA]. Both cannot be true as stated.

## Recommendation

**Pass at this time; revisit only after reference checks resolve both contradictions.** Signal 5.4 / Coverage 81%. This is a high-coverage record whose verified portion is genuinely strong — the problem is that the two most impressive claims are the two that fail verification. Market and product are credible; the integrity dimension caps the founder axis. The specific reference calls that would reopen this: (a) a DataLoom investor or the Cisco corp-dev contact confirming transaction character; (b) any DataLoom employee confirming the founder's start date.

## Company snapshot

Corevance is an AI copilot that drafts and maintains SOC 2 / ISO 27001 evidence for mid-market software companies [prod-10 · 0.85 · corr — product is live, verified against public site and docs]. Compliance evidence collection is a persistent, budgeted pain; the category has proven willingness to pay [mkt-10 · 0.8 · corr].

## Investment hypotheses

- Verified product exists and demos well [prod-10].
- Founder's Stripe-era infrastructure background, where verifiable, is real [team-13 · 0.75 · corr — two conference talks, dated].
- Claimed $480K ARR would imply strong early PMF **if confirmed** [trac-10 · 0.4 · self — deck only; no external corroboration found].

## SWOT

- **S:** live product [prod-10]; credible domain choice [mkt-10].
- **W:** the traction claim is entirely self-reported [trac-10]; both differentiating biography claims are contradicted [team-10, team-12].
- **O:** incumbent tooling (Vanta, Drata) is checklist-oriented; agentic drafting is a plausible wedge [mkt-11 · 0.6 · single].
- **R:** incumbents ship the same feature [risk-10 · 0.7 · single]; founder-integrity risk as above.

## Problem & product

Mid-market companies spend hundreds of hours assembling audit evidence annually. Corevance connects to cloud infra, drafts evidence artifacts, and flags drift between controls and reality [prod-10]. Two named design partners appear in the deck; neither is externally verifiable [trac-11 · 0.4 · self] [flag: customer references unavailable at this stage].

## Traction & KPIs

$480K ARR claimed [trac-10 · self — **uncorroborated**]. Customer count: 14 claimed [trac-11 · self]. Churn, CAC, sales cycle: not disclosed [flag]. Usage metrics: not disclosed [flag].

**Financials & round structure: raising $1.5M; only the deck's summary slide available [fin-10 · 0.4 · self].**
**Cap table: not disclosed [flag].**

## Due diligence log

Checked: EDGAR Form D for DataLoom (negative) [dd-02]; Cisco acquisition record (negative) [dd-03]; founder conference talks (positive) [team-13]; product existence (positive) [prod-10]; timeline assembly across four dated sources [dd-04].
**Open:** (open-10) transaction character of the DataLoom outcome; (open-11) employment timeline; (open-12) any single customer reference confirming contracted revenue.

---

# MEMO 3 — Parcelmind (Founder C: inbound, invest with condition)

**To:** IC · **Re:** Parcelmind — $100K conditional recommendation

## Recommendation

**Invest $100K, conditional on one customer reference confirming contracted (not LOI) revenue.** Signal 6.9 / Coverage 64%. Two-founder team with verifiable domain history; honest-looking record with one load-bearing ambiguity: the deck's "12 customers, $40K ACV" [trac-20 · 0.5 · self] is consistent with pilots/LOIs rather than contracts, and the red-team pass found phrasing elsewhere in the deck ("committed pipeline") that suggests exactly that [risk-20 · 0.6 · inferred]. One reference call resolves it. Outcome view: 55% failure, 30% modest, 15% strong.

## Company snapshot

Parcelmind automates freight-quote comparison and carrier negotiation for mid-size shippers, a market where equivalent quotes vary severalfold and procurement is manual [mkt-20 · 0.7 · single]. Product is live with API integrations to two major TMS platforms [prod-20 · 0.8 · corr].

## Investment hypotheses

- Founders spent a combined 9 years at freight brokers/TMS vendors — verified via dated talks and a patent filing [team-20 · 0.85 · corr]. Strong founder-market fit.
- Wedge (quote comparison) has immediate, measurable ROI; expansion into full procurement automation [hyp-20 · 0.5 · inferred].
- If ACV claim is contracted revenue, implied early PMF is strong for stage [trac-20].

## SWOT

- **S:** verified domain depth [team-20]; live integrations [prod-20].
- **W:** revenue character unverified [trac-20]; sales cycle in logistics is long [mkt-21 · 0.6 · single].
- **O:** incumbents serve enterprise; mid-market underserved [mkt-22 · 0.6 · single].
- **R:** TMS platforms could build natively [risk-21 · 0.7 · single].

## Problem & product

Mid-size shippers overpay because quote comparison across carriers is manual and slow. Parcelmind ingests shipment specs, collects quotes, and negotiates within guardrails set by the shipper [prod-20]. [Verified against product documentation; no customer-side verification yet — flag.]

## Traction & KPIs

12 customers claimed, $40K ACV claimed [trac-20 · self]. Growth trajectory: not derivable from materials [flag]. Unit economics: not disclosed [flag].

**Financials & round structure: $1.2M round, 18-month claimed runway [fin-20 · 0.4 · self].**
**Cap table: not disclosed [flag].**

## Due diligence log

Checked: founder employment history via talks + patent [team-20]; product/integration claims vs. documentation [prod-20]; market sizing sources [mkt-20].
**Open:** (open-20) revenue character — the condition on this investment; (open-21) churn among the 12 claimed customers; (open-22) whether either TMS partner has a competing roadmap item.

---

## Notes for the build (why the memos look like this)

1. **Recommendation is always first**, in Bessemer's register: a number, a decision, and the named evidence the decision turns on. Judges read this block and skim the rest.
2. **Contradictions outrank everything** — Memo 2 opens with them before the recommendation. The brief scores "flag contradictions before they reach the investor"; put them literally first.
3. **Trust notation is inline, not in an appendix.** Every load-bearing sentence carries its claim ID. This is the format constraint your synthesizer enforces.
4. **Gaps use the brief's own phrasing** ("not disclosed," "unavailable at this stage") — judges wrote those strings; echo them.
5. **The three recommendations differ on purpose:** invest (thin record, verified velocity), pass (rich record, broken integrity), conditional (one gap, one call). Together they show the system produces *decisions*, not summaries — and that coverage and signal move independently, which is the whole argument.
6. **"What would change our mind"** in Memo 1 and the named reference calls in Memos 2–3 are the value-of-information feature. Keep them — they're what makes these read as analyst work rather than generated text.
