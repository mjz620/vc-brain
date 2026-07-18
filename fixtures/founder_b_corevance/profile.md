# Founder B — Corevance (credentialed inbound, contradictions found)

Inbound application (deck + name). High-coverage record whose verified portion is genuinely strong — but
the two most impressive claims are the two that fail verification. Recommendation target: **pass; revisit
only after reference checks resolve both contradictions. Signal 5.4 / Coverage 81%.**

## Profile

- **Founder:** Devin Marsh. Public profile shows full-time **Stripe** employment (Infrastructure Engineer)
  **2017 → mid-2020**. Deck claims prior startup **DataLoom** "acquired by Cisco, 2021" and founded
  **March 2019** with Marsh as **full-time CEO**.
- **Company — Corevance:** AI copilot that drafts and maintains **SOC 2 / ISO 27001** evidence for
  mid-market software companies. Connects to cloud infra, drafts evidence artifacts, flags drift between
  controls and reality. **Product is live** (verified against public site + docs). Two named design
  partners in the deck; neither externally verifiable.
- **Round:** raising **$1.5M**. Only a summary slide available. **Cap table: not disclosed.**

## Raw signals

### Deck (self-reported) — `source_type=deck`
- `source_url`: fixtures/founder_b_corevance/deck-summary.txt — `observed_at`: 2026-07-18
- Claims: DataLoom "acquired by Cisco, 2021" [team-10]. DataLoom raised a **$4M seed** [supports dd-02
  search]. Founder full-time CEO of DataLoom from **March 2019** [team-12]. **$480K ARR** [trac-10].
  **14 customers** [trac-11]. Two design partners named (Northwind Systems, Halcyon Labs) — unverifiable.
- Churn, CAC, sales cycle: **not disclosed**. Usage metrics: **not disclosed**.

### Web / public profile (self-reported)
- `source_url`: https://www.linkedin-alternative.example/in/devin-marsh (public bio mirror) —
  `observed_at`: 2026-07-18 — Stripe Infrastructure Engineer, 2017 → mid-2020. [team-11]

### Product existence (verified)
- `source_url`: https://corevance.example / https://docs.corevance.example — `observed_at`: 2026-07-18 —
  Product live, matches deck description. [prod-10]

### Conference talks (verified, dated) — the *real* part of the biography
- `source_url`: https://qconsf.example/2018/marsh-ledger-infra — "Building Reliable Payment Ledgers",
  QCon SF, **2018-11**, speaker affiliation **Stripe**. [team-13]
- `source_url`: https://strangeloop.example/2019/marsh-infra-scale — "Infra at Scale", Strange Loop,
  **2019-09**, speaker affiliation **Stripe**. [team-13]

### Negative-result claims (first-class evidence — Block 1 must store these with their search URLs)
- **dd-02 — EDGAR Form D for DataLoom's claimed $4M seed: NOT FOUND.** `source_url`:
  https://efts.sec.gov/LATEST/search-index?q=%22DataLoom%22&forms=D — full-text search returns no Form D
  filing for DataLoom. `observed_at`: 2026-07-18. Corroboration: corr (0.9).
- **dd-03 — Cisco 2021 acquisition announcements do NOT include DataLoom.** `source_url`:
  https://newsroom.cisco.example/2021/acquisitions — DataLoom absent from Cisco's 2021 acquisition list.
  `observed_at`: 2026-07-18. Corroboration: corr (0.85). Consistent with an unannounced acquihire —
  materially different from the "successful exit" framing.
- **dd-04 — timeline assembled across four dated sources** (Stripe bio, two talks with Stripe affiliation,
  DataLoom deck founding date) → overlap is provable.

### Market (single-source)
- Compliance evidence collection is a persistent, budgeted pain; category proven willingness to pay.
  [mkt-10] Incumbents **Vanta, Drata** are checklist-oriented; agentic drafting is a plausible wedge.
  [mkt-11] Risk: incumbents ship the same feature. [risk-10]

## Seeded contradictions (must survive — this is the flagging demo)
1. **Claimed exit vs. public record.** Deck: DataLoom "acquired by Cisco, 2021" [team-10 · CONTRA]. No
   Form D for the claimed $4M seed [dd-02] and DataLoom absent from Cisco's 2021 acquisitions [dd-03].
2. **Timeline overlap.** Full-time Stripe through mid-2020 [team-11] vs. DataLoom founded March 2019 with
   Marsh as full-time CEO [team-12 · CONTRA]. Both cannot be true as stated.

## Score & open items
- Signal **5.4** / Coverage **81%**. The integrity dimension caps the founder axis; market + product credible.
- Open: **open-10** transaction character of the DataLoom outcome; **open-11** employment timeline;
  **open-12** any single customer reference confirming contracted revenue.

## Claim-ID cross-reference (→ target-memos.md MEMO 2)
| Claim | Fact | Source | Tier |
|---|---|---|---|
| team-10 | DataLoom "acquired by Cisco, 2021" | deck | CONTRA |
| dd-02 | No Form D for DataLoom $4M seed (EDGAR search, negative) | EDGAR search URL | corr |
| dd-03 | DataLoom absent from Cisco 2021 acquisitions | Cisco newsroom | corr |
| team-11 | Full-time Stripe through mid-2020 | public bio | self |
| team-12 | DataLoom founded Mar 2019, founder full-time CEO | DataLoom materials/deck | CONTRA |
| team-13 | Stripe-era infra background real (2 dated talks) | QCon 2018 + Strange Loop 2019 | corr |
| prod-10 | Live SOC2/ISO27001 evidence copilot | site + docs | corr |
| mkt-10 | Compliance-evidence pain, willingness to pay | market | corr |
| mkt-11 | Vanta/Drata checklist-oriented; agentic wedge | market | single |
| trac-10 | $480K ARR claimed, uncorroborated | deck | self |
| trac-11 | 14 customers / 2 design partners, unverifiable | deck | self |
| fin-10 | Raising $1.5M, summary slide only | deck | self |
| risk-10 | Incumbents ship same feature | inference | single |
| dd-04 | Timeline assembled across four dated sources | multi-source | — |
| open-10/11/12 | transaction character · timeline · customer ref | DD open items | — |
