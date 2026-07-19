import { useEffect, useState } from "react";
import * as api from "../api";
import FlowField from "../components/FlowField";

/* The entry screen before the dashboard — a self-contained dark hero (independent
   of the app's light/dark toggle). Its stat row is live, fetched from the same
   endpoints the app uses everywhere else, so the first thing a VC sees is proof
   this is a real running system, not a mockup. The workflow section is an
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
      <FlowField />
      <div className="landing-inner">
        <header className="landing-nav">
          <BrainMark />
          <span className="landing-wordmark">VC Brain<span className="dot">.</span></span>
        </header>

        <section className="landing-hero">
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
                <Stat icon={<IconSignal />} v={stats.signals} k="signals ingested" />
                <Stat icon={<IconFounders />} v={stats.founders} k="founders resolved" />
                <Stat icon={<IconLogged />} v={stats.dropped} k={<>unresolved, logged<br />not discarded</>} />
              </>
            ) : (
              <span className="landing-loading">loading live counts…</span>
            )}
          </div>

          <button className="landing-cta" onClick={onEnter}>
            Enter the pipeline <span aria-hidden="true">→</span>
          </button>
        </section>

        <section className="landing-flow">
          <h2 className="landing-flow-h">How the machine reasons</h2>
          <p className="landing-flow-sub">
            Four stages turn scattered public signals into an auditable decision.
            Each step below names exactly what goes in, what it does, and what
            comes out — and whether it's a fixed formula or an LLM judgment.
          </p>
          <ol className="landing-flow-list">
            {FLOW.map((s) => (
              <li key={s.n} className="flow-stage">
                <span className="flow-num">{s.n}</span>
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
              </li>
            ))}
          </ol>
        </section>

        <p className="landing-foot">
          Curious how a specific number is computed? Every Signal, Coverage, axis,
          and Trust score in the app carries an ⓘ that opens its exact formula —
          or see the full Methodology page inside.
        </p>
      </div>
    </div>
  );
}

function Stat({ icon, v, k }: { icon: React.ReactNode; v: number; k: React.ReactNode }) {
  return (
    <div className="landing-stat">
      <span className="landing-stat-icon" aria-hidden="true">{icon}</span>
      <span className="landing-stat-v">{v}</span>
      <span className="landing-stat-k">{k}</span>
    </div>
  );
}

/* Low-poly neural mark — nodes wired into a brain silhouette. Mirrors the favicon. */
function BrainMark() {
  return (
    <svg className="landing-logo" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <path
        d="M11 6.5C7.5 6.5 5 9 5 12c-2 .8-3 2.5-3 4.5S3 20 5 20.5c0 3 2.5 5 6 5 1.6 0 3-.6 4-1.6M11 6.5c1.4 0 3 .8 4 2.2M11 6.5c1.8-2 4.6-2 6.5-.5M21 6C24.5 6 27 8.5 27 11.5c2 .8 3 2.5 3 4.5s-1 3.7-3 4.2c0 3-2.5 5.3-6 5.3-1.6 0-3-.6-4-1.6V8.7M15 8.7v15.2"
        stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"
      />
      {[[5,12],[2.8,16.5],[11,6.5],[15,8.7],[21,6],[27.2,11.5],[30,16],[9,17],[19,14],[23,20],[15,24]].map(
        ([cx, cy], i) => <circle key={i} cx={cx} cy={cy} r="1.15" fill="currentColor" />
      )}
    </svg>
  );
}

function IconSignal() {
  return (
    <svg viewBox="0 0 20 20" fill="none">
      <circle cx="10" cy="10" r="2" fill="currentColor" />
      <path d="M6 6a5.7 5.7 0 000 8M14 6a5.7 5.7 0 010 8M3.5 3.5a9.2 9.2 0 000 13M16.5 3.5a9.2 9.2 0 010 13"
        stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
function IconFounders() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="7" cy="7" r="2.6" /><path d="M2.5 16.5a4.5 4.5 0 019 0" />
      <path d="M13.5 5a2.6 2.6 0 010 5M14.5 16.5a4.5 4.5 0 00-2-3.7" />
    </svg>
  );
}
function IconLogged() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round">
      <path d="M10 2.5l6 2.4v4.6c0 3.6-2.5 6-6 8-3.5-2-6-4.4-6-8V4.9l6-2.4z" />
      <path d="M7.5 10l1.8 1.8L13 8" strokeLinecap="round" />
    </svg>
  );
}
