# VC Brain — Architecture

An evidence-first sourcing and diligence engine: it finds founders **before they
fundraise**, scores what is **verifiable** rather than who is connected, and produces a
**gap-honest $100K memo** in minutes. Everything traces back to a source; nothing in an
output path is fabricated.

Stack: Python + SQLite (single file, zero ops) · FastAPI · React/Vite SPA. Provider-agnostic
LLM wrapper (OpenAI or Anthropic) with a disk replay cache so the whole demo is deterministic.

---

## 1. The pipeline at a glance

The brief's four stages — Sourcing → Screening → Diligence → Decision — run on top of three
layers: **Memory** (data), **Intelligence** (reasoning), **Experience** (UI). Two intake tracks
(outbound scan + inbound apply) converge into one funnel.

```mermaid
flowchart LR
    subgraph INTAKE["Two tracks, one funnel"]
        OUT["OUTBOUND scanner<br/>GitHub · HN · arXiv<br/>ProductHunt · YC"]
        IN["INBOUND apply<br/>deck + company name"]
    end

    OUT --> MEM
    IN --> MEM

    subgraph MEM["① MEMORY (SQLite, append-only)"]
        SIG["signals<br/>(nothing discarded)"]
        RES["entity resolution<br/>≥2 keys → founder"]
        FS["Founder Score<br/>(persistent, never resets)"]
        SIG --> RES --> FS
    end

    MEM --> SCR
    SCR["② SCREENING<br/>3 axes, never averaged<br/>+ first-pass kill"] --> DIL
    DIL["③ DILIGENCE<br/>claim ledger + Trust Score<br/>adversarial debate"] --> DEC
    DEC["④ DECISION<br/>memo + recommendation<br/>gaps flagged, not filled"]

    DEC -.high-signal outbound.-> ACT["ACTIVATE<br/>outreach draft<br/>(cites triggering signal)"]
    ACT -.triggers a real application.-> IN

    THESIS["THESIS ENGINE (YAML)"] -.filters scan.-> OUT
    THESIS -.scoring lens.-> SCR
    THESIS -.scoring lens.-> DEC

    style MEM fill:#16223c,stroke:#6f9bff,color:#e7ebf1
    style THESIS fill:#2a2113,stroke:#e0a63a,color:#e7ebf1
    style ACT fill:#10241b,stroke:#3bce8e,color:#e7ebf1
```

The **thesis config** is applied twice — as a filter on the scanner and as a scoring lens in
screening/decision — so the same founder pool yields different answers for different funds.

---

## 2. Layers → stages → code

```mermaid
flowchart TB
    subgraph EXP["EXPERIENCE — React SPA (5 stage-pages)"]
        P1["Sourcing"]:::ui
        P2["Screening"]:::ui
        P3["Diligence"]:::ui
        P4["Memo & Decision"]:::ui
        P5["Thesis & Query"]:::ui
    end

    subgraph API["FastAPI — app/server.py (read-mostly JSON)"]
        E["/api/sourcing · /founders · /trace<br/>/query · /activate · /apply · /channels"]:::api
    end

    subgraph INT["INTELLIGENCE"]
        SC["app/screening<br/>axes · firstpass · thesis"]:::int
        DG["app/diligence<br/>workers · ledger · adjudicate<br/>debate · synthesizer · critic · validate"]:::int
        DC["app/decision<br/>gap render · per-axis · latency"]:::int
        QN["app/query · app/activate"]:::int
    end

    subgraph MM["MEMORY — app/memory"]
        DB["db.py (schema + triggers)"]:::mem
        RS["resolve.py · ingest.py"]:::mem
        FSC["founder_score.py"]:::mem
    end

    subgraph SRC["SOURCES — app/sources"]
        AD["github · hn · arxiv · producthunt · yc<br/>scanner · velocity · http (cached)"]:::src
    end

    LLM["app/llm.py + app/cache.py<br/>provider-agnostic + replay cache"]:::sys

    EXP --> API --> INT
    INT --> MM
    SRC --> MM
    DG --> LLM
    SC --> LLM
    QN --> LLM

    classDef ui fill:#16223c,stroke:#6f9bff,color:#e7ebf1
    classDef api fill:#1d2330,stroke:#8b95a5,color:#e7ebf1
    classDef int fill:#20261a,stroke:#3bce8e,color:#e7ebf1
    classDef mem fill:#2a1f2c,stroke:#c586c0,color:#e7ebf1
    classDef src fill:#2a2113,stroke:#e0a63a,color:#e7ebf1
    classDef sys fill:#2c1614,stroke:#f0655a,color:#e7ebf1
```

---

## 3. Memory — the data foundation

SQLite, ten tables. The design commitment is **"nothing discarded"**: the `signals` table is
append-only, *enforced by database triggers* (not convention), and signals that fail entity
resolution are logged rather than dropped.

```mermaid
flowchart LR
    RAW["raw event<br/>(repo, post, deck…)"] --> DH{"dedup hash<br/>source+url+norm(content)"}
    DH -->|new| S[("signals<br/>APPEND-ONLY<br/>trigger-enforced")]
    DH -->|duplicate| REJ["rejected<br/>(original untouched)"]

    S --> ER{"entity resolution<br/>≥2 co-occurring keys?"}
    ER -->|yes| F[("founders")]
    ER -->|no / ambiguous| DL[("droplog<br/>logged, not dropped")]

    F --> FS["Founder Score<br/>append-only history<br/>→ trend for free"]
    F --> CL[("claims — the ledger<br/>every claim ≥1 signal")]

    style S fill:#16223c,stroke:#6f9bff,color:#e7ebf1
    style DL fill:#2c1614,stroke:#f0655a,color:#e7ebf1
    style CL fill:#20261a,stroke:#3bce8e,color:#e7ebf1
```

**Tables:** `founders`, `signals`, `claims`, `resolutions`, `droplog`, `axis_scores`,
`adjudications`, `memos`, `latency`, `kill_log`, `outreach`.

**Founder Score** (persistent, per-person, never resets — distinct from the per-opportunity
3-axis score). Computed *mechanically* from evidence, so it is deterministic:

| Dimension | Source signal |
|---|---|
| execution_velocity | trailing-6-week commit cadence |
| community_pull | stars / HN points (log-scaled) |
| domain_breadth | number of distinct source channels |
| integrity | fraction of claims **not** contradicted |
| verified_depth | fraction of claims corroborated |

A dimension with no evidence is `None` (**unassessed**), never a fabricated zero — so a
cold-start founder gets a **low-coverage flag, not a low score**.

---

## 4. Sourcing — built deepest (the brief's priority)

```mermaid
flowchart TB
    T["thesis.topics<br/>(drives the queries)"] --> SCAN["scanner.run_scan"]
    SCAN --> G[github]:::a
    SCAN --> H[hn]:::a
    SCAN --> A[arxiv]:::a
    SCAN --> PH[producthunt]:::a
    SCAN --> YC[yc]:::a
    G & H & A & PH & YC --> ING["ingest + resolve"]
    ING --> W{"--watch loop"}
    W -->|new signal crosses<br/>conviction threshold| RESCR["auto re-screen"]
    RESCR -->|best axis ≥ threshold| ACT["ACTIVATE draft<br/>cites triggering signal URL<br/>(mechanically verified)"]
    classDef a fill:#2a2113,stroke:#e0a63a,color:#e7ebf1
    style ACT fill:#10241b,stroke:#3bce8e,color:#e7ebf1
```

Each adapter is ~40 lines: fetch → normalize to a Signal → ingest. Every live HTTP response is
cached by `(url, params)`; in replay mode a cache miss is a hard error — that's what makes the
demo deterministic. **Activate** drafts cold outreach and *rejects any draft that doesn't cite
the exact triggering signal* (no-fabrication guardrail applied to outreach too).

---

## 5. Screening — three axes, never averaged

```mermaid
flowchart LR
    SUM["founder summary<br/>signals + Founder Score<br/>(as ONE input)"] --> KILL{"first-pass<br/>kill screen"}
    KILL -->|non-viable| LOG["kill_log<br/>+ reason"]
    KILL -->|viable| AX
    subgraph AX["3 independent axes — NO composite key exists"]
        FA["Founder<br/>strong/mixed/weak"]:::x
        MA["Market<br/>bullish/neutral/bear"]:::x
        IA["Idea vs Market<br/>survives/pivot-bet/weak"]:::x
    end
    AX --> TR["trend arrow<br/>(from append-only history)"]
    classDef x fill:#16223c,stroke:#6f9bff,color:#e7ebf1
```

Each axis is an independent LLM call against an anchored rubric; the result dict deliberately has
**no average/blended/overall field** (test-enforced). The disagreement between axes *is* the
signal an investor needs. The kill screen only removes obvious non-starters — never for thin
records, unverified claims, or off-sector fit (those are scoring matters).

---

## 6. Diligence — the claim ledger + adversarial Trust Score

This is where fragmented signals become verified, tiered claims. Contested claims go to trial.

```mermaid
flowchart TB
    EV["founder evidence<br/>(all signals)"] --> WK
    subgraph WK["workers extract claims (grounded, parallel)"]
        WF["founder<br/>(deepest: timeline +<br/>integrity cross-check)"]:::w
        WM[market]:::w
        WR[risk / red-team]:::w
        WT[traction]:::w
    end
    WK --> LED["ledger.assemble<br/>rubric trust by tier"]
    LED --> CT{"contested?<br/>(contradicted / self-reported)"}
    CT -->|yes, top N| ADJ
    CT -->|no| KEEP["keep rubric trust"]

    subgraph ADJ["fact-layer debate (per claim)"]
        PR["Prosecutor<br/>argue false"]:::p
        DF["Defender<br/>argue holds"]:::d
        JG["Judge<br/>sets tier + trust<br/>OVERRIDES rubric"]:::j
        PR --> DF --> JG
    end

    ADJ --> STORE[("claims + adjudications<br/>(full transcript persisted)")]
    KEEP --> STORE
    STORE --> DEB

    subgraph DEB["decision-layer debate"]
        BU["Bull → invest"]:::p
        BE["Bear → pass/condition"]:::d
        RJ["Judge → recommendation"]:::j
        BU --> BE --> RJ
    end

    RJ --> SYN["Synthesizer<br/>memo, contradictions first,<br/>every sentence cites a claim"]
    SYN --> VAL{"mechanical validator<br/>(NO LLM)"}
    VAL -->|fake claim id / uncited quant| CRIT["critic: 1 revision round"]
    VAL -->|clean| MEMO[("memo + recommendation")]
    CRIT --> MEMO

    classDef w fill:#20261a,stroke:#3bce8e,color:#e7ebf1
    classDef p fill:#2c1614,stroke:#f0655a,color:#e7ebf1
    classDef d fill:#10241b,stroke:#3bce8e,color:#e7ebf1
    classDef j fill:#2a2113,stroke:#e0a63a,color:#e7ebf1
```

**Trust tiers** (self-reported hard-capped at 0.6):

| Tier | Rubric trust | Meaning |
|---|---|---|
| corroborated | 0.85 | ≥2 independent sources agree |
| single_source | 0.60 | one external source |
| self_reported | 0.40 | deck/self only, no external backing |
| contradicted | 0.30 → judge lowers | external record conflicts with the claim |

A **negative-result search** ("EDGAR: no Form D found") is a first-class claim, with the search
URL as its source. The mechanical validator makes the pipeline *structurally* unable to
hallucinate a citation: any memo sentence or debate turn citing a claim id not in the ledger is
rejected.

---

## 7. Decision — and why gaps are a feature

The decision layer is pure assembly (no LLM, deterministic, zero cost): it pulls the stored
recommendation, renders the three axes **side by side**, and mechanically reports gaps.

```mermaid
flowchart LR
    CLAIMS["ledger claims"] --> GAP{"required field<br/>has a claim?"}
    GAP -->|yes| OK["field: disclosed [ids]"]
    GAP -->|no| FLAG["field: not disclosed<br/>(fixed phrase — NEVER a value)"]
    style FLAG fill:#2a2113,stroke:#e0a63a,color:#e7ebf1
```

The gap branch emits only the brief's own phrasing and is tested to contain **no digits** — a
placeholder value reaching a memo is treated as a P0 bug. Cap table missing → *"Cap table: not
disclosed"*, rendered as a deliberate badge, not an apology.

---

## 8. Agentic Traceability — the signature interaction

Every conclusion cites the exact data point that drove it. Clicking any citation in the UI walks
the full chain — this is the highest-leverage stretch goal, made visible.

```mermaid
flowchart LR
    C["memo sentence<br/>[team-01 · 0.10 · CONTRA]"]:::click --> CLM["Claim<br/>text · trust · tier"]
    CLM --> EVD["Evidence snippet"]
    EVD --> SG["Source signal<br/>dated, linked URL"]
    SG --> HOW["How trust was set"]
    HOW --> RUB["rubric anchor"]
    HOW --> TRIAL["OR: rubric value struck through<br/>+ prosecutor/defender/judge transcript"]
    classDef click fill:#16223c,stroke:#6f9bff,color:#e7ebf1
    style TRIAL fill:#2c1614,stroke:#f0655a,color:#e7ebf1
```

Every hop is data already in the DB (`claims.signal_ids` → `signals`; `adjudications` transcript)
— zero new reasoning, pure exposure.

---

## 9. Determinism & the demo

```mermaid
flowchart LR
    LIVE["live run<br/>(needs API key)"] -->|caches every response| CACHE[("app/cache<br/>llm + http")]
    CACHE --> REPLAY["--replay<br/>(no key, cache-only,<br/>miss = hard error)"]
    REPLAY --> REBUILD["scripts/rebuild_demo.py<br/>fresh DB in <1s<br/>+ docs/EVAL.md"]
    style CACHE fill:#16223c,stroke:#6f9bff,color:#e7ebf1
```

The logical LLM cache key is `(tier + prompt + schema)` — provider-independent — so a cache
seeded with one provider replays with **no key at all**. `python scripts/rebuild_demo.py`
rebuilds the entire demo database deterministically from committed caches and writes the eval
summary.

### Tavily ingestion

Open-web founder research (Tavily news search + extract, `app/sources/tavily.py`) is ingested
as **signals only**: untrusted web content never becomes a claim directly — claims derived from
it pass the same worker extraction, corroboration rubric, and adjudication as every other
source, and a lone article stays `single_source`. Tavily additionally applies prompt-injection
filtering on its side before content reaches us; we still treat article text as data, never as
instructions. All Tavily calls are replay-cached with a persisted per-month credit cap, and
news enrichment is refused for the three demo fixture founders so cached demo claims can never
be silently regenerated.

---

## 10. The three demo founders (the whole argument, in three rows)

| Founder | Track | Signal / Coverage | Decision | What it proves |
|---|---|---|---|---|
| **Tracewell** | outbound, cold-start | 8.4 / 46% | invest, conditional on incorporation | thin record ≠ weak; verified velocity is fundable |
| **Corevance** | inbound, credentialed | 4.6 / 92% | **pass** | rich record, but the two best claims fail verification — contradictions surfaced first |
| **Parcelmind** | inbound | 6.3 / 69% | invest, conditional on 1 reference call | one honest ambiguity, one named call resolves it |

Coverage and signal move **independently** — that is the equitable-allocation thesis of the whole
system, visible in one screen.

---

*Generated as a companion to `docs/vc-brain-spec.md` (design) and `docs/SUBMISSION.md` (rubric
write-up). Diagrams render on GitHub and any Mermaid-aware viewer.*
