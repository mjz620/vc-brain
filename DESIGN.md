---
name: VC Brain
description: Evidence-first venture sourcing & diligence engine — an editorial terminal for the $100K decision.
colors:
  accent: "#3358d4"
  accent-weak: "#eaeffd"
  ink: "#10141a"
  paper: "#f6f7f9"
  paper-sink: "#eef0f3"
  panel: "#ffffff"
  line: "#e4e7ec"
  muted: "#667085"
  faint: "#98a2b3"
  corroborated: "#157f4c"
  corroborated-bg: "#e6f4ec"
  single-source: "#a5620a"
  single-source-bg: "#fbf0dc"
  contradiction: "#b42318"
  contradiction-bg: "#fbeae8"
typography:
  page-title:
    fontFamily: "Newsreader, Iowan Old Style, Palatino, Georgia, serif"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.01em"
  memo-body:
    fontFamily: "Newsreader, Iowan Old Style, Palatino, Georgia, serif"
    fontSize: "15.5px"
    fontWeight: 400
    lineHeight: 1.7
    letterSpacing: "normal"
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, -apple-system, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.06em"
  data:
    fontFamily: "SFMono-Regular, ui-monospace, JetBrains Mono, Menlo, monospace"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  xs: "5px"
  chip: "6px"
  sm: "8px"
  md: "12px"
  pill: "20px"
  focus: "4px"
spacing:
  base: "8px"
  half: "4px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "5px 11px"
  button-ghost:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "5px 11px"
  tier-corroborated:
    backgroundColor: "{colors.corroborated-bg}"
    textColor: "{colors.corroborated}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  tier-contradicted:
    backgroundColor: "{colors.contradiction-bg}"
    textColor: "{colors.contradiction}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  input-field:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "9px 12px"
  claim-row:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
---

# Design System: VC Brain

## 1. Overview

**Creative North Star: "The Editorial Terminal"**

VC Brain is a Bloomberg terminal that reads like a magazine. The reasoning — memos, page titles, evidence excerpts — is set in a warm editorial serif (Newsreader) so a recommendation reads like a document an analyst would trust, while every number, score, and citation is set in tabular sans and mono so the data stays terminal-precise. The two registers coexist on purpose: analytical depth served at editorial legibility, which is the literal expression of "Notion-approachable, Bloomberg-deep." The interface is calm and confident; it never hypes, because its entire value is that the evidence holds up.

The surface is flat and tonally layered — three cool near-neutrals (paper, paper-sink, panel) stack to create depth without a single decorative shadow. One accent, Evidence Blue, does all the load-bearing work: it is the color of a citation, a current selection, a primary action, and nothing else. Around it sits a strict semantic trust vocabulary — green for corroborated, amber for single-source, red for contradicted, slate for self-reported — that appears identically on every screen so the analyst learns it once. Components are crisp and tactile: thin borders at rest, a decisive accent shift and lift on interaction.

This system explicitly rejects three things. It is **not consumer fintech** — no pastel rounding, no playful illustration, no Robinhood softness; this is investment-committee work. It is **not enterprise legacy** — no cluttered toolbars, dated corporate blues, or heavy chrome. And it is **not generic SaaS/AI-dashboard slop** — no purple-blue AI gradients, no gradient hero cards, no identical icon-card grids, no big-number KPI template.

**Key Characteristics:**
- Serif for reasoning, tabular sans/mono for data — the two-voice split is the identity.
- Flat, tonally-layered surfaces; depth from stacked neutrals, not shadow.
- One accent (Evidence Blue) reserved for citations, selection, and primary actions.
- A semantic trust-tier color language, always paired with a text label.
- Density that serves the task; the three screening axes are shown side by side, never blended.

## 2. Colors

A cool, near-neutral paper base carrying one decisive blue accent and a four-color semantic trust vocabulary. Values below are the light theme (canonical); a full dark theme mirrors every token (see the sidecar) and drops shadows entirely.

### Primary
- **Evidence Blue** (`#3358d4`, dark `#6f9bff`): The single load-bearing accent. It is the color of a citation chip, the current nav item, a selected claim row, a primary button, and the latency "total" marker. It signals "this is a link to proof or the thing you're acting on" — never decoration.
- **Evidence Blue Wash** (`#eaeffd`, dark `#16223c`): The tint behind selected/active states, citations, and the sourcing suggestion callout. Evidence Blue at low volume.

### Neutral
- **Ink** (`#10141a`, dark `#e7ebf1`): Primary text and data. High-contrast against every surface.
- **Slate** (`#667085`, dark `#8b95a5`): Secondary/muted text — labels, sub-copy, table meta. Meets AA on paper and panel.
- **Faint** (`#98a2b3`, dark `#626d7d`): Tertiary text only — column headers, timestamps, placeholder hints. Never body copy.
- **Paper** (`#f6f7f9`, dark `#0d1017`): App background. A true-cool near-white (chroma near zero), deliberately not a warm cream.
- **Paper Sink** (`#eef0f3`, dark `#12161f`): The recessed layer — hover fills, chip backgrounds, nav-number tiles.
- **Panel** (`#ffffff`, dark `#161b24`): The raised content surface — cards, tables, inputs, the memo.
- **Line** (`#e4e7ec`, dark `#232a35`): Hairline borders and dividers. 1px only.

### Tertiary (Semantic trust + decision vocabulary)
- **Corroborated Green** (`#157f4c` on `#e6f4ec`): Corroborated claims, bullish/invest states, improving trends.
- **Single-Source Amber** (`#a5620a` on `#fbf0dc`): Single-source claims, neutral/conditional states, caution.
- **Contradiction Red** (`#b42318` on `#fbeae8`): Contradicted claims, pass/bearish states, declining trends. The color that says "read this first."
- **Self-Reported Slate** (Slate on Paper Sink): Unverified/self-reported claims — deliberately colorless, because absence of corroboration is the point.

### Named Rules
**The One Voice Rule.** Evidence Blue is the only accent. It appears on citations, current selection, and primary actions — nothing else. Its rarity is what makes a citation legible as a link to proof.

**The Trust-Vocabulary Rule.** Green/amber/red/slate mean corroborated/single-source/contradicted/self-reported everywhere, without exception. A tier color is never reused for decoration, and it never travels without its text label.

## 3. Typography

**Display / Reasoning Font:** Newsreader (with Iowan Old Style, Palatino, Georgia fallback)
**Body / UI Font:** Inter (with system-ui fallback)
**Data / Citation Font:** SFMono-Regular (with ui-monospace, JetBrains Mono, Menlo fallback)

**Character:** A contrast-axis pairing, not a similar-fonts clash: a warm optical serif for anything that reads like prose (memos, page titles, evidence quotes) against a neutral grotesque for UI and a mono for identifiers. The serif makes a recommendation feel authored and considered; the sans/mono keep the data terminal-crisp. `font-variant-numeric: tabular-nums` is applied to every figure so numbers align in columns.

### Hierarchy
- **Page Title** (Newsreader 600, 28px, lh 1.1, -0.01em): Page headers ("Sourcing", "Memo & Decision"). Serif, so the section reads editorial.
- **Memo Heading** (Newsreader 600, 17px): Section headings inside a memo ("## Recommendation").
- **Memo Body** (Newsreader 400, 15.5px, lh 1.7): The memo prose itself — the one place the analyst reads at length. Kept to a comfortable measure, not full-width.
- **Body** (Inter 400, 14px, lh 1.55): Default UI text, table cells, descriptions. Prose blocks cap at 640px (~70ch).
- **Label** (Inter 600, 11px, uppercase, 0.06em): Section labels, table column headers, block titles, badge text. The quiet all-caps that organizes the terminal.
- **Data / Citation** (SFMono 500, 12px, tabular): Claim ids and inline citations like `[team-02 · 0.90 · corroborated]`. Mono signals "this is a precise identifier."

### Product Density Scale

The five roles above name the *intent*; a data-dense product terminal legitimately uses more steps than a brand ramp. The full functional type scale in use (all px): **28** (page title) · **27** (verdict) · **20** (rec headline) · **19** (brand) · **17** (memo heading) · **15.5** (memo body) · **14** (base UI) · **13.5 / 13 / 12.5** (dense table + control text) · **12** (citations) · **11.5 / 11 / 10.5** (labels, meta, column headers) · **9.5** (the gap micro-badge). These are intentional and on-system — density serves the task; they are not off-ramp drift.

### Named Rules
**The Two-Voice Rule.** Serif is for reasoning a human reads (memos, titles, quotes). Sans and mono are for data and chrome. Never set a memo in sans; never set a data label in serif.

## 4. Elevation

Flat by default. Depth comes from tonal layering — Paper (background) → Panel (raised card/table/memo) → Evidence Blue Wash (active) — not from shadow. In light mode a single near-invisible ambient shadow lifts panels a hair off the page; in dark mode shadows are removed entirely and the panel's own lighter tone carries the elevation. There is no shadow scale, no z-lift on hover; interaction is signaled by border-color and background, not by casting shadow.

### Shadow Vocabulary
- **Ambient panel** (`box-shadow: 0 1px 2px rgba(16,24,40,.06), 0 1px 3px rgba(16,24,40,.08)`): The only shadow. Applied to panels, tables, inputs, and the evidence rail in light mode. Set to `none` in dark mode.

### Named Rules
**The Flat-Terminal Rule.** Surfaces are flat. Depth is tonal, not cast. If a component needs a shadow to separate from its background, the wrong background tone is being used — reach for Panel over Paper instead.

## 5. Components

Components are crisp and tactile: quiet at rest with a thin `Line` border, decisive on interaction — border and text shift to Evidence Blue, primary fills brighten. Transitions are fast (150–200ms) and convey state only.

### Buttons
- **Shape:** Gently rounded (8px, `{rounded.sm}`).
- **Primary** (`.minibtn.primary`): Evidence Blue fill, white text, 5px 11px padding. Hover brightens ~8%.
- **Ghost** (`.minibtn`): Panel background, Ink text, 1px Line border. Hover shifts border and text to Evidence Blue. This is the default button; primary is reserved for the one real action on a view.
- **Disabled:** 55% opacity, default cursor. No color change.

### Chips (trust tiers, sources, badges)
- **Trust-tier chip:** Pill (20px), tier color on its paired tint, mono, tabular. Always carries the tier's text label plus the trust value — never hue alone.
- **Decision badge** (`.badge`): Pill, 11px uppercase 0.06em, semantic color on tint — invest→green, pass→red, conditional→amber, none→slate.
- **Source tag** (`.src`): Slate on Paper Sink pill, 11px — channel provenance.

### Cards / Containers
- **Corner Style:** 12px (`{rounded.md}`) for blocks and tables, 8px for compact rows.
- **Background:** Panel, on the Paper page.
- **Shadow Strategy:** Ambient panel shadow (light) / none (dark) — see Elevation.
- **Border:** 1px Line. Nested cards are forbidden.
- **Internal Padding:** 14–16px for blocks, 8–12px for rows.

### Inputs / Fields
- **Style:** Panel background, 1px Line border, 8px radius, 9px 12px padding, ambient shadow.
- **Placeholder:** Faint (still AA-legible), never lighter.
- **Focus:** Border shifts to Evidence Blue with a visible focus ring; no glow.

### Navigation
- **Style:** Fixed left rail, Panel background, mirroring the pipeline (Sourcing → Screening → Diligence → Decision → Thesis). Items are Slate; hover fills Paper Sink and darkens to Ink; the active item takes Evidence Blue Wash with Blue text and a filled Blue number tile.
- **Mobile:** Below 860px the rail collapses to a horizontal wrapping bar; numbers and sub-label hide.

### Signature Component — The Evidence Rail + Citation
The trust story made visible. Inline citations (`.cite`) are mono, Evidence-Blue-on-wash, clickable buttons embedded in serif memo prose. Clicking one opens the **Evidence Rail** (`.evidence`) — a sticky Panel bound by a full Evidence Blue border (the one place a colored border is intentional and full, never a stripe) — which shows the claim, its trust tier, the source card (domain chip, serif italic excerpt, retrieval date), and the prosecutor→defender→judge adjudication. Wide tables live inside a `.tablewrap` (`overflow-x: auto`) so the page body never scrolls sideways.

## 6. Do's and Don'ts

### Do:
- **Do** reserve Evidence Blue (`#3358d4`) for citations, current selection, and the one primary action per view. Its rarity is the point (The One Voice Rule).
- **Do** keep green/amber/red/slate meaning corroborated/single-source/contradicted/self-reported on every screen, and **always pair a tier color with its text label** — the trust vocabulary must survive color-blindness and glare (WCAG-AA + colorblind-safe, per PRODUCT.md).
- **Do** set memos, page titles, and evidence quotes in Newsreader serif; set all data, labels, and citations in Inter/mono with `tabular-nums`.
- **Do** show the three screening axes and the Signal/Coverage split as **separate values**, never averaged into one reassuring number.
- **Do** render gaps and contradictions with weight — a flagged "not disclosed" or a pinned contradiction is a feature of the surface, in the brief's own words.
- **Do** convey depth with tonal layers (Paper → Panel → Wash) and interaction with border/background shifts.
- **Do** guard every animation (currently the `pulse` on live stages) with `@media (prefers-reduced-motion: reduce)` — reduced motion is a PRODUCT.md commitment.

### Don't:
- **Don't** look like **consumer fintech** — no pastel rounding, playful illustration, or Robinhood/Cash-App softness.
- **Don't** look like **enterprise legacy (Salesforce-y)** — no cluttered toolbars, dated corporate blues, heavy chrome, or low information-to-pixel ratio.
- **Don't** look like **generic SaaS/AI-dashboard slop** — no purple-blue AI gradients, gradient hero cards, identical icon-card grids, or the big-number KPI template.
- **Don't** use gradient text, decorative glassmorphism, or `border-left`/`border-right` color stripes as accents (use full borders, tints, or nothing).
- **Don't** cast shadows to separate a surface — fix the background tone instead (The Flat-Terminal Rule).
- **Don't** introduce a second accent hue, and never reuse a trust-tier color for decoration.
- **Don't** nest cards, and don't let a wide table scroll the page body — wrap it in `.tablewrap`.
