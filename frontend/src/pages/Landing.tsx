import { useEffect, useState } from "react";
import * as api from "../api";

/* The entry screen before the dashboard. Its stat row is live — fetched from the
   same endpoints the app uses everywhere else — so the first thing a VC sees is
   proof this is a real running system, not a mockup. The workflow section is an
   interpretable, plain-language account of exactly what the machine does at each
   stage, and which parts are mechanical vs. an LLM judgment. */

const FLOW = [
  {
    n: "1", label: "Sourcing", kind: "mechanical",
    in: "GitHub, Hacker News, arXiv, ProductHunt, YC — and inbound decks",
    does: "Dedupe, timestamp, and resolve raw signals into founders on ≥2 co-occurring identity keys. Nothing is discarded — unresolved signals stay in a drop-log.",
    out: "Founders ranked by thesis fit, each with a persistent Founder Score",
  },
  {
    n: "2", label: "Screening", kind: "llm",
    in: "A founder's resolved signals + your fund thesis",
    does: "A fast kill-screen removes clear non-starters, then three axes — Founder, Market, Idea-vs-Market — are scored independently against your thesis. They are never averaged; the disagreement between them is the signal.",
    out: "Three separate axis scores + stances + trend arrows",
  },
  {
    n: "3", label: "Diligence", kind: "both",
    in: "The deck, external evidence, and live market research",
    does: "Workers extract discrete claims; each gets a Trust Score from its corroboration tier. Contested claims go to a prosecutor → defender → judge debate. A no-LLM validator rejects any citation to a claim that doesn't exist.",
    out: "A claim ledger — every claim with a trust tier and a link to its source",
  },
  {
    n: "4", label: "Decision", kind: "both",
    in: "The scored axes + the claim ledger",
    does: "Synthesize a memo: recommendation first, contradictions surfaced, missing data flagged in the brief's own words (never fabricated). Every sentence cites the claim ids it rests on.",
    out: "An investment memo you can take to IC — every number one click from its evidence",
  },
];

const KIND_LABEL: Record<string, string> = {
  mechanical: "mechanical", llm: "LLM judgment", both: "mechanical + LLM",
};

export default function Landing({ onEnter }: { onEnter: () => void }) {
  const [stats, setStats] = useState<{ signals: number; founders: number; dropped: number } | null>(null);

  useEffect(() => {
    Promise.all([api.getQuality(), api.getSourcing("config/thesis_preseed_ai_infra.yaml")])
      .then(([q, s]) => setStats({
        signals: q.dedup_protected_signals,
        founders: s.founders.length,
        dropped: s.droplog_count,
      }))
      .catch(() => {});
  }, []);

  return (
    <div className="landing">
      <div className="landing-inner">
        <div className="landing-brand">VC Brain<span className="dot">.</span></div>
        <h1 className="landing-h1">A $100K decision, in 24 hours,<br />with every number traceable.</h1>
        <p className="landing-sub">
          An evidence-first sourcing and diligence engine. Every claim carries a
          Trust Score and a link to its source; every score on every page shows
          the formula that produced it. Nothing here is asserted without a way
          to check it.
        </p>

        <div className="landing-stats">
          {stats ? (
            <>
              <Stat v={stats.signals} k="signals ingested" />
              <Stat v={stats.founders} k="founders resolved" />
              <Stat v={stats.dropped} k="unresolved, logged not discarded" />
            </>
          ) : (
            <span className="muted">loading live counts…</span>
          )}
        </div>

        <button className="minibtn primary landing-cta" onClick={onEnter}>
          Enter the pipeline →
        </button>

        <div className="landing-flow">
          <div className="landing-flow-h">How the machine reasons</div>
          <p className="landing-flow-sub">
            Four stages turn scattered public signals into an auditable decision.
            Each step below names exactly what goes in, what it does, and what
            comes out — and whether it's a fixed formula or an LLM judgment.
          </p>
          {FLOW.map((s, i) => (
            <div key={s.n} className="flow-stage">
              <div className="flow-rail">
                <span className="nav-n">{s.n}</span>
                {i < FLOW.length - 1 && <span className="flow-line" />}
              </div>
              <div className="flow-body">
                <div className="flow-title">
                  {s.label}
                  <span className={`flow-kind flow-kind-${s.kind}`}>{KIND_LABEL[s.kind]}</span>
                </div>
                <dl className="flow-io">
                  <dt>in</dt><dd>{s.in}</dd>
                  <dt>does</dt><dd>{s.does}</dd>
                  <dt>out</dt><dd>{s.out}</dd>
                </dl>
              </div>
            </div>
          ))}
        </div>

        <p className="landing-foot">
          Curious how a specific number is computed? Every Signal, Coverage, axis,
          and Trust score in the app carries an ⓘ that opens its exact formula —
          or see the full Methodology page inside.
        </p>
      </div>
    </div>
  );
}

function Stat({ v, k }: { v: number; k: string }) {
  return (
    <div className="landing-stat">
      <span className="landing-stat-v">{v}</span>
      <span className="landing-stat-k">{k}</span>
    </div>
  );
}
