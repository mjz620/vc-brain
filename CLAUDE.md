# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

# PROJECT: VC Brain (hackathon, solo, hard deadline)

Spec: `vc-brain-spec.md`. Target output format + demo fixtures: `target-memos.md`. Read the spec's block table once; after that, read only the section for the current block.

## 5. Block-by-Block Protocol

**One block at a time. Runnable at every checkpoint. Stop means stop.**

- Build exactly one block from spec §5, then STOP. Do not start the next block, do not "get a head start," do not scaffold future blocks.
- Every block ends runnable: a command I can execute against real or fixture input, printed as the last line of your summary.
- End every block with a checkpoint report, max 6 lines:
  ```
  BLOCK n DONE
  Built: [what exists now, 1-2 lines]
  Run: [exact command]
  Verified: [what you checked and the result]
  Flags: [anything I should look at, or "none"]
  ```
- Commit at every checkpoint: `git commit -m "block-n: <one line>"`. Never batch commits across blocks.
- If a block reveals a spec problem, say so in Flags and propose the smallest fix. Don't silently redesign.
- Deadline rule: if a sub-feature is fighting you for >20 min, stub it, flag it, move on. The spec's cut order (§5) decides what dies — not effort already sunk.

## 6. Checkpoint Acceptance Gates

Block-specific checks I will run before saying "continue":

- **Block 1 (Memory):** claims table stores a negative-result claim (e.g. "EDGAR search for X: no filing found" with the search URL as source). Signals table is append-only. Dedup hash rejects a duplicate.
- **Block 2 (Scanner):** GitHub + HN adapters return real signals for a live query; entity resolution drop-log is populated; no LinkedIn scraping anywhere.
- **Block 3 (Screening):** three axes render separately with trends; nothing averages them.
- **Block 4 (Diligence):** synthesizer output for Corevance fixtures reproduces the contradiction-first structure of `target-memos.md`; mechanical validator rejects a sentence with a fake claim ID.
- **Block 5 (Decision):** missing data renders the brief's phrasing ("not disclosed"), never a generated value.
- **Block 6 (Frontend):** click-to-evidence works; no build step; one HTML file + FastAPI.

## 7. Token Efficiency

**Spend tokens on code and checks, not on narration and re-reading.**

- Never paste back file contents I already have. Reference paths + line ranges.
- Never re-print a whole file after editing it. Show the diff or nothing.
- Read files surgically: the function you're changing, not the module. Re-read only what your own edits invalidated.
- No progress narration ("Now I will create..."). Do the thing; report in the checkpoint format.
- Prefer targeted edits over regenerating files. Regenerating a file you wrote 20 minutes ago is a bug.
- Tests and dev runs use fixtures/`--replay`, never live API calls, unless the block IS the live adapter. Cache every live response the first time you fetch it.
- Command output: pipe through `tail`/`grep` for long output; don't dump full logs into context. Quiet flags on installers (`pip -q`, `npm --silent`).
- Batch related shell commands with `&&` instead of one call per command.
- When debugging, state the hypothesis in one line, run the narrowest check that tests it, and don't re-run the full pipeline to verify a one-module fix.
- If context is getting heavy mid-block, write state to `NOTES.md` (current block, what's done, next step) rather than relying on re-reading history.

## 8. Project Guardrails

- **Fixture integrity is sacred.** Never regenerate numbers, dates, or names in `target-memos.md` or seeded fixture data. The Corevance contradictions must keep contradicting. If a fixture needs to change, flag it and wait.
- **Worker prompts and scoring rubrics are human-owned.** Create the files with `# TODO(mingjia)` placeholders; never fill or "improve" them. I iterate these by hand.
- **Negative results are claims.** The schema must represent "searched X, found nothing" as first-class evidence with a source URL.
- **No fabricated data anywhere in output paths.** A gap renders as a flagged gap. This is scored behavior; treat any generated placeholder value in a memo as a P0 bug.
- **Demo determinism.** Anything shown in the demo must run from cached/replay state. Live calls are for the recorded live-run segment only.
