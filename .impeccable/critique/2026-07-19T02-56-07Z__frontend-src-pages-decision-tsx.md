---
target: Decision page (memo + evidence rail)
total_score: 32
p0_count: 0
p1_count: 3
timestamp: 2026-07-19T02-56-07Z
slug: frontend-src-pages-decision-tsx
---
Method: dual-agent (A: design-review · B: detector+static-evidence)

## Design Health Score — 32/40 (Good)

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Skeletons + verbatim errors are strong; ↓ PDF opens a blank tab with no feedback |
| 2 | Match System / Real World | 4 | Domain-true language ("turns on", prosecutor/defender/judge, corroborated) |
| 3 | User Control and Freedom | 3 | Persistent switcher + closeable trace, but trace rail is not Esc-dismissible |
| 4 | Consistency and Standards | 3 | Tier language exemplary; axis row is a bare div-onClick while every other trace opener is a real button |
| 5 | Error Prevention | 3 | Ask disabled on empty/busy; validator strips fabricated citation ids |
| 6 | Recognition Rather Than Recall | 3 | Inline citations strong; clickable axis rows + graph chains are undiscoverable (cursor+title only) |
| 7 | Flexibility and Efficiency | 2 | No keyboard path through graph/axes; no focus-visible anywhere; power user is mouse-bound |
| 8 | Aesthetic and Minimalist | 3 | Beautiful type system, but latency strip + default-open graph + meters crowd the core memo |
| 9 | Error Recovery | 4 | Friendly status map + verbatim server detail; refusal renders as an honest gap |
| 10 | Help and Documentation | 3 | page-sub + many titles; no first-run guidance for tier/coverage/adjudication jargon |
| **Total** | | **32/40** | **Good — strong substance, weak on a11y + decision-moment hierarchy** |

## Anti-Patterns Verdict

**LLM assessment:** Not slop. Clears every absolute ban — no side-stripe card accents, no gradient text, no glassmorphism, no hero-metric template, no identical card grid. The "Editorial Terminal" system is executed with real discipline (serif memo, mono tabular citations, single Evidence-Blue accent, tier colors that always carry a text label). A fluent Linear/Bloomberg/Notion user would trust it. The risk is not fakeness — it's density.

**Deterministic scan:** Detector is HTML/CSS-only and cannot parse TSX, so it silently covered nothing on the .tsx sources (exit 0, []). On the built bundle it flagged one `overused-font` warning (Inter, dist/index.html:9) — cosmetic. All substantive evidence is hand-computed static inspection (contrast, motion, focus, responsive).

**Visual overlays:** None — no browser automation in this environment. That is the fallback signal; the computed-contrast + static-focus evidence stands in for a rendered pass.

## Overall Impression

On substance this is the strongest surface in the app: the trace chain (claim → source card → prosecutor/defender/judge, with the rubric-trust struck through and replaced by the adjudicated value) makes the reasoning auditable, not asserted — it is the trust-through-traceability thesis made literal. What holds it back is a mismatch between what the page *is* and what it *shows first*: on a page named "Decision," the decision is the smallest confident element (an 11px pill), while a sub-second engineering latency strip and a default-open provenance graph compete for attention above the reasoning. And underneath the polish sits a real accessibility debt — no focus styles, no reduced-motion guard, mouse-only trace openers, and low-contrast faint text — that a screen-reader or keyboard user hits immediately.

## What's Working

1. **Negative/refusal results as first-class citizens.** Refused answers render as gaps not errors; "no raw signal on record — the source card is the whole provenance"; the validator openly reports stripped fake citations. Almost no product does this; it reads as unusually credible.
2. **Deliberately un-averaged scoring.** Signal and Coverage are two separate meters ("never one number"); the three axes are shown independently. This directly refuses the single-vanity-score slop the anti-references warn against.
3. **The rubric→judge delta in the trace.** Showing mechanical rubric trust struck through and replaced by the adjudicated value is Bloomberg-deep detail done right — auditable reasoning.
4. **Honest sparkline** — a single data point renders a flat tick, never a fake trend.

## Priority Issues

- **[P1] Accessibility: no keyboard operability or focus styling.** Axis rows are `<div onClick>` (Decision.tsx:108) and provenance nodes are `<g onClick>` in an SVG marked `role="img"` (components.tsx:312) — both mouse-only. There are **zero** `:focus-visible`/`outline` rules in the entire stylesheet, so even the real buttons show no keyboard focus. The trace rail isn't Esc-dismissible and its close control is a bare `×` with no aria-label. *Why it matters:* keyboard/SR users (Sam) cannot open a trace or see where they are — WCAG 2.1.1 / 2.4.7. *Fix:* make axis rows `<button>`; give graph nodes focus+Enter or a parallel text list; add a global accent `:focus-visible` ring; add Esc-to-close + `aria-label="Close"`. **Command: /impeccable harden.**
- **[P1] Contrast: `--faint` text fails AA in both themes, plus two dark-theme fills.** `--faint` (#98a2b3 light ≈ 2.4–2.6:1; #626d7d dark ≈ 3.3–3.6:1) is used for timestamps, section/column labels, placeholders, and the "+N more" — the highest-volume defect. Dark-theme **white-on-accent** primary button = 2.69 and **white-on-`--mid` gap-badge** = 2.17 both fail badly (the gap-badge is scored, first-class behavior). Light tier chips good/mid on their tints (4.44 / 4.27) miss AA-normal at ~11px. *Fix:* darken `--faint` to ~#6b7280 for text roles; darken dark-accent or use ink text on primary buttons in dark; darken the dark gap-badge fill or use dark text. **Command: /impeccable colorize.**
- **[P1] prefers-reduced-motion is not honored (a stated commitment).** No `@media (prefers-reduced-motion: reduce)` exists anywhere; the infinite `.pulse` on the busy "Ask" button and the skeleton shimmer run regardless. *Why:* breaks the explicit PRODUCT.md accessibility promise + WCAG 2.3.3. *Fix:* global reduce block zeroing animation/transition; swap the busy-pulse for a static "asking…" label. **Command: /impeccable harden.**
- **[P2] The decision verdict is under-weighted; latency + open graph add noise above the reasoning.** The invest/pass pill is the smallest confident element (11px), smaller than the $ amount (16px) — hierarchy inverted at the exact decision point. Above the memo the analyst meets ~10 competing regions (badge, name, sparkline, amount, turns-on, what-would-change, 3 axes, gaps, latency, open graph) — working memory fails. *Fix:* elevate the verdict to the card's hero line paired with the check size and "what would change our mind"; default the provenance graph to closed (Decision.tsx:145); demote the latency strip behind a disclosure or into a footer. **Command: /impeccable layout (then /impeccable distill).**
- **[P3] No confident closing "act on it" affordance.** The analyst's actual deliverable — the PDF — is a tiny buried header link with no confirmation or preview, so the page ends on a fizzle instead of a hand-off (peak-end miss). *Fix:* add an end-of-memo primary "Export IC memo (PDF)" + copy-citations action. **Command: /impeccable clarify (then /impeccable polish).**
- **[P3] Memo renderer silently drops structure.** The markdown renderer handles only #/##/###, `-`, and `**bold**` (components.tsx:142); an ordered list (`1.`), table, or link in the memo renders as raw paragraph text — a Riley break as memo generation grows. *Fix:* handle ordered lists + linkify, or constrain generation. **Command: /impeccable harden.**

## Persona Red Flags

**Sam (accessibility-dependent) — the most-broken persona.** Locked out three ways: reduced-motion ignored; `--faint` timestamps/labels below AA in both themes; axis rows and provenance nodes are mouse-only with an interactive SVG mislabeled `role="img"`, and no focus ring exists anywhere so keyboard traversal is invisible. The close `×` reads as "multiplication sign" to a screen reader.

**The IC-accountable analyst (project persona) — served on substance, failed on gravitas.** The trace chain, refusal honesty, and un-averaged scoring are exactly what let them defend a check — but the verdict they must present renders as an 11px pill, the deliverable PDF is a buried tooltip-link with no confirmation, and a sub-second latency strip on a $100K decision reads as the builder's metric, quietly eroding authority.

**Riley (stress-tester) — concrete breaks:** long founder names have no truncation on `.rec-card h1` and appear twice (Decision.tsx:60 header + :78 card); a memo containing a table or numbered list renders raw; a long axis stance string overflows the fixed 74px `.axline .num`. (The trace-404 and fake-citation-in-Ask paths, by contrast, degrade gracefully.)

## Minor Observations

- Founder identity renders twice within ~20px (Decision.tsx:60 and :78) — two `<h1>` on one page.
- `decClass` decision-color mapping is fragile `.includes()` string-matching (components.tsx:286) — "invest-conditional" only resolves to amber because "conditional" is tested before "invest"; a reordered label mis-colors.
- On mobile, `.memo-wrap { flex-direction: column-reverse }` puts the trace panel *above* the memo, so tapping an inline citation opens a panel off-screen upward — a scroll jump (Casey).
- Refusal renders in amber (`--mid`). Penalizing the system's honesty with a caution color subtly discourages the exact behavior you want.
- Dead CSS: `.ev-tier` superseded by TierChip (pre-existing — flag, don't delete).

## Questions to Consider

- Should a $100K go/no-go surface show sub-second pipeline latency at all — whose need does that serve, the analyst's or the demo's?
- Four routes to the same trace (turns-on chips, inline citations, axis-row click, graph nodes): confident redundancy, or four half-committed affordances where one bold one — the memo citations — would carry the whole load?
- The recommendation is the smallest confident element on a page named "Decision." If you stripped everything but the badge, the amount, and "what would change our mind," would the analyst decide faster and trust it more?
