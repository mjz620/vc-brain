# Founder C — Parcelmind (inbound, invest with condition)

Inbound application (deck + name). Two-founder team with verifiable domain history; honest-looking record
with **one load-bearing ambiguity**: the deck's revenue character. Recommendation target: **invest $100K,
conditional on one customer reference confirming contracted (not LOI) revenue. Signal 6.9 / Coverage 64%.**

## Profile

- **Founders:** Priya Anand and Marcus Ohl. Combined **9 years** at freight brokers / TMS vendors
  (verified via dated talks + a patent filing). Strong founder-market fit.
- **Company — Parcelmind:** automates freight-quote comparison and carrier negotiation for mid-size
  shippers — a market where equivalent quotes vary severalfold and procurement is manual. **Product is
  live** with API integrations to two major TMS platforms (**MercuryGate**, **Blue Yonder TMS**).
- **The ambiguity:** deck claims **12 customers, $40K ACV** but elsewhere uses the phrase "committed
  pipeline" — consistent with **pilots / LOIs** rather than signed contracts. One reference call resolves it.
- **Round:** **$1.2M**, **18-month claimed runway**. **Cap table: not disclosed.**

## Raw signals

### Deck (self-reported) — `source_type=deck`
- `source_url`: fixtures/founder_c_parcelmind/deck-summary.txt — `observed_at`: 2026-07-18
- Claims: 12 customers [trac-20], $40K ACV [trac-20], $1.2M round / 18-month runway [fin-20], live
  integrations with MercuryGate + Blue Yonder [prod-20]. Uses "committed pipeline" phrasing [red-team bait
  for risk-20]. Growth trajectory + unit economics **not disclosed**.

### Founder history (verified, dated)
- `source_url`: https://manifestvegas.example/2022/anand-freight-procurement — Priya Anand, "Fixing
  Freight Procurement", Manifest 2022, affiliation **FreightWaves / TMS vendor**. `observed_at`: 2026-07-18.
- `source_url`: https://patents.google.example/patent/US11500000 — patent "Dynamic carrier rate
  negotiation", inventor **Marcus Ohl**, assignee a TMS vendor, filed 2021. `observed_at`: 2026-07-18.
  Together these verify combined ~9 yrs freight/TMS depth. [team-20]

### Product / integrations (verified)
- `source_url`: https://docs.parcelmind.example/integrations — documents live API integrations with
  MercuryGate + Blue Yonder TMS. `observed_at`: 2026-07-18. [prod-20]

### Market (single-source)
- Freight quote comparison manual/slow; equivalent quotes vary severalfold. [mkt-20] Sales cycle in
  logistics is long. [mkt-21] Incumbents serve enterprise; mid-market underserved. [mkt-22] Risk: TMS
  platforms could build natively. [risk-21]

### Red-team bait (must be caught, not fabricated)
- The deck says "12 customers, $40K ACV" **and** "committed pipeline" — the red-team pass must flag that
  "committed pipeline" is consistent with pilots/LOIs, not contracts. [risk-20 · inferred] This is
  open-20, the condition on the investment. Do **not** resolve it to a number — flag it.

## Score & open items
- Signal **6.9** / Coverage **64%**. Outcome view: 55% failure, 30% modest, 15% strong.
- Open: **open-20** revenue character (the condition); **open-21** churn among the 12 claimed customers;
  **open-22** whether either TMS partner has a competing roadmap item.

## Claim-ID cross-reference (→ target-memos.md MEMO 3)
| Claim | Fact | Source | Tier |
|---|---|---|---|
| mkt-20 | Freight quote comparison manual; quotes vary severalfold | market (single) | single |
| prod-20 | Live, API integrations to MercuryGate + Blue Yonder | docs | corr |
| team-20 | Combined 9 yrs freight/TMS; talk + patent | Manifest 2022 + patent | corr |
| trac-20 | 12 customers, $40K ACV claimed | deck | self |
| risk-20 | "committed pipeline" phrasing → pilots/LOIs not contracts | red-team inference | inferred |
| hyp-20 | Wedge (quote comparison) → full procurement automation | inferred | inferred |
| mkt-21 | Logistics sales cycle long | market | single |
| mkt-22 | Incumbents enterprise; mid-market underserved | market | single |
| risk-21 | TMS platforms could build natively | inference | single |
| fin-20 | $1.2M round, 18-month runway | deck | self |
| open-20/21/22 | revenue character · churn · partner roadmap | DD open items | — |
