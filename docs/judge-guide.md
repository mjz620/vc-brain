# Judge guide — 60 seconds to the good parts

Open the app (deployed URL, or `uvicorn app.server:app` → http://localhost:8000).
The sidebar mirrors the pipeline: Sourcing → Screening → Diligence → Memo & Decision.

## The click path

1. **Sourcing** — the outbound feed found these founders before they raised.
   Press **Scan now** (pick a source, e.g. Hacker News): a REAL live fetch runs
   against the public API, new signals resolve or land in the drop-log — nothing
   discarded, and the channel-yield funnel updates.
2. **Apply your own company** (right column): company name + a few deck sentences
   is the whole bar. Watch the run: screen → extract → adjudicate → debate →
   synthesize, each stage live with real timings. ~2 minutes later you have a
   memo for a company this system has never seen. Non-viable ideas are killed at
   first pass and say so honestly — no memo is fabricated.
3. **Diligence** (pick Corevance — the seeded contradiction case): contradicted
   claims are pinned first. Click one: the full trace — evidence link, source
   signals, and the prosecutor → defender → judge transcript that overrode the
   rubric trust. The validator card above it is a no-LLM check that every cited
   claim id exists.
4. **Memo & Decision** — three axes scored independently (never averaged), each
   with a trend; gaps render as "not disclosed", never a made-up number. Ask the
   memo a question: answers cite claim ids and refuse when the ledger can't
   support an answer. The provenance section maps decision → claims → sources.
5. **Thesis & Query** — switch the fund thesis (bottom-left) and watch the same
   founders re-rank; type a compound query ("technical founder, AI infra,
   enterprise traction, no prior VC backing") — evaluable criteria filter
   mechanically, non-evaluable ones are flagged and ignored, never guessed.

## What to look for (maps to the rubric)

- **Data architecture**: /api/quality — per-channel funnel, drop reasons,
  the arXiv pool honestly labeled "awaiting a second identity key."
- **Trust**: every claim has a resolvable evidence URL (negative results carry
  the search URL that returned nothing); per-claim Trust Score by corroboration
  tier; contested claims adjudicated by debate.
- **Utility**: the latency strip on every memo — first signal → decision.
- **Honesty**: the kill log, the drop-log, refused answers, flagged gaps.

## Notes

- Free-tier hosting sleeps: the first load may take ~40s. Everything after is fast.
- Live endpoints (apply / scan / query / ask) are rate-limited per client — the
  demo spends real API budget.
