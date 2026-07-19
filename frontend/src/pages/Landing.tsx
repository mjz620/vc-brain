import { useEffect, useState } from "react";
import * as api from "../api";

/* The entry screen before the dashboard. Its own stat row is live — fetched from
   the same endpoints the app uses everywhere else — so the first thing a VC sees
   is proof this is a real, running system, not a mockup. */
const STAGES = [
  { n: "1", label: "Sourcing", desc: "Outbound scan (GitHub, HN, arXiv, ProductHunt, YC) finds founders before they raise; inbound applications land in the same funnel." },
  { n: "2", label: "Screening", desc: "Three independent axes — Founder, Market, Idea-vs-Market — scored against your fund thesis. Never averaged; the disagreement is the signal." },
  { n: "3", label: "Diligence", desc: "Every claim traces to evidence with its own Trust Score. Contested claims go through a prosecutor → defender → judge debate before they reach you." },
  { n: "4", label: "Decision", desc: "A memo you can act on: recommendation first, gaps flagged in the brief's own words, every number one click from its source." },
];

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
              <div className="landing-stat">
                <span className="landing-stat-v">{stats.signals}</span>
                <span className="landing-stat-k">signals ingested</span>
              </div>
              <div className="landing-stat">
                <span className="landing-stat-v">{stats.founders}</span>
                <span className="landing-stat-k">founders resolved</span>
              </div>
              <div className="landing-stat">
                <span className="landing-stat-v">{stats.dropped}</span>
                <span className="landing-stat-k">unresolved, logged not discarded</span>
              </div>
            </>
          ) : (
            <span className="muted">loading live counts…</span>
          )}
        </div>

        <button className="minibtn primary landing-cta" onClick={onEnter}>
          Enter the pipeline →
        </button>

        <div className="landing-stages">
          {STAGES.map((s) => (
            <div key={s.n} className="landing-stage">
              <span className="nav-n">{s.n}</span>
              <div>
                <div className="landing-stage-h">{s.label}</div>
                <p className="landing-stage-p">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
