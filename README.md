# FirstSignal

**The VC brain for evidence-grounded founder discovery.**
Find them first. Verify everything. Decide in 24 hours.

Built solo for the Maschmeyer Group VC Brain Challenge.

FirstSignal finds exceptional founders before they start fundraising, then verifies
every claim about them against external evidence. Seven adapters scan public builder
ecosystems; signals resolve into persistent founder identities; an adversarial
diligence pipeline produces an investment memo where every number carries a trust
tier and a link to its source — and a gap renders as a flagged gap, never a
generated value.

---

## What it does

**Sourcing → Screening → Diligence → Decision**, as one evidence-preserving pipeline.

- **Outbound sourcing.** GitHub, Hacker News, arXiv, Product Hunt, YC cohorts, a
  company launch tracker, and open-web search. Inbound decks (PDF or pasted text)
  enter the same funnel.
- **Identity resolution.** A signal links to a founder only on **two co-occurring
  identity keys**. Platform domains and their subdomains can never act as identity.
  Unresolved signals go to a visible drop log rather than being silently merged.
- **Persistent Founder Score, separate from Coverage.** A sparse record reads as
  *uncertain*, not *weak* — the two numbers never blend.
- **Independent screening.** Founder, Market and Idea-vs-Market, scored through a
  configurable thesis lens and never averaged.
- **Adversarial diligence.** Contested claims go to prosecutor / defender / judge
  agents whose verdict can override the base trust rubric. Contradictions lead the
  memo.
- **Decision.** invest / pass / conditional with the claims it turns on, an explicit
  "what would change our mind", gaps, per-stage latency, grounded Q&A, PDF export.
- **Sourcing graph.** Channels, startups, founders and early investors — joining
  curated public outcome references with live pipeline yield, and feeding the fund's
  own decisions back to the channel that sourced each founder.

The headline result: **Corevance** (polished inbound, 92% coverage, Signal 4.6) is a
**pass** — its deck claims an acquisition with no public record and a CEO tenure
overlapping the same founder's employment elsewhere. **Tracewell** (never applied,
46% coverage, Signal 8.4) is an **invest at $100,000**. Higher coverage did not win;
verifiable evidence did.

---

## Quickstart

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                       # install
cp .env.example .env          # add OPENAI_API_KEY (or ANTHROPIC_API_KEY) + TAVILY_API_KEY
uv run python cli.py init     # create the local SQLite database
```

Run the app — API plus the built frontend on one port:

```bash
uv run uvicorn app.server:app --reload
# http://localhost:8000
```

Everything below runs from cache with `--replay`, so it costs nothing and is
deterministic:

```bash
uv run python cli.py --replay diligence --fixture founder_b_corevance --print-memo
uv run python cli.py --replay decision  --fixture founder_b_corevance
uv run python cli.py scan --topic "llm agents"        # live outbound scan
```

`--replay` is a global flag and goes *before* the subcommand.

Tests (SQLite only, no network, no API keys needed):

```bash
uv run pytest -q
```

Frontend development:

```bash
cd frontend && npm install && npm run dev    # or: npm run build
```

---

## Configuration

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Agent layer. Either one works. |
| `TAVILY_API_KEY` | External evidence retrieval during diligence. |
| `DATABASE_URL` | Postgres in deployment. Unset → local SQLite. |
| `VC_REPLAY=1` | Force cache-only mode; a cache miss fails instead of calling out. |
| `VC_MAX_ADJUDICATIONS` | Cap on adversarial adjudications per run (default 6). |

Theses live in `config/*.yaml` and drive both the sourcing scanner and the scoring
lens. Worker prompts and rubrics are in `prompts/` and are hand-tuned.

---

## Design decisions worth knowing

**Signals are append-only**, enforced by a database trigger — provenance cannot be
rewritten after the fact. Deleting a signal is not a supported operation.

**Guardrails are code, not prompt instructions**, so a model cannot argue with them.
A validator rejects citations to claim IDs that don't exist. The integrity gate
counts contradicted founder claims mechanically, so a "pass" citing contradictions
the ledger doesn't hold is rejected by construction.

**Negative results are first-class claims.** "Searched EDGAR for X, found no filing"
is stored with the search URL that returned nothing.

**Runs replay deterministically.** Every external call is cached on first use; strict
replay fails on a miss rather than silently going live.

---

## Layout

```
app/
  sources/     7 outbound adapters behind one interface
  memory/      append-only signals, entity resolution, Founder Score
  screening/   three independent axes + first-pass kill screen
  diligence/   workers → claim ledger → adjudication → debate → memo
  decision/    recommendation + brief assembly
  api/         network graph, evidence, methodology, quality
frontend/      React + TypeScript (Vite)
prompts/       hand-tuned worker prompts and rubrics
config/        thesis definitions
docs/          architecture, spec, submission materials
```

**Stack:** React + TypeScript, FastAPI, Supabase PostgreSQL (SQLite locally),
Tavily, OpenAI/Anthropic, ReportLab. 74 automated tests.

More detail in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md); the challenge
submission write-up is in [`docs/submission-description.md`](docs/submission-description.md).
