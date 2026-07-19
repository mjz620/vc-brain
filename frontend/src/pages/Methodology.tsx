import { ReactNode, useEffect, useState } from "react";
import * as api from "../api";
import type { Methodology } from "../api";
import { Err, Skeleton } from "../components";

/* Page 7 — the whole scoring system in one place. Every number in this app
   traces to a formula or a rubric here; nothing is a black box, and nothing on
   this page is hand-typed prose — it's fetched live from the same constants
   and prompt files the scoring code itself reads. */
export default function MethodologyPage() {
  const [m, setM] = useState<Methodology | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { api.getMethodology().then(setM).catch((e) => setErr(e.message)); }, []);

  return (
    <div>
      <div className="page-h">
        <h1>Methodology</h1>
        <p className="page-sub">
          Every score in this app is either a mechanical formula over evidence in
          Memory, or an LLM judgment against a written rubric — never a magic
          number. This page is generated from the same constants and prompt
          files the scoring code reads at run time, so it can't drift from what
          actually happened.
        </p>
      </div>
      {err && <Err msg={err} />}
      {!m && !err && <Skeleton lines={12} />}
      {m && (
        <>
          <MethodBlock title={m.signal.name} what={m.signal.what_it_is}
            formula={m.signal.formula}>
            <table className="method-table">
              <thead><tr><th>dimension</th><th>weight</th><th>formula</th></tr></thead>
              <tbody>
                {Object.entries(m.signal.dimensions).map(([k, desc]) => (
                  <tr key={k}>
                    <td>{k.replace(/_/g, " ")}</td>
                    <td className="it-num">{m.signal.weights[k]}</td>
                    <td className="muted">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="method-note">
              Weights renormalize over whatever's actually assessed — a cold-start
              founder with no claims yet doesn't get penalized for the two
              claims-derived dimensions being absent; the composite is a weighted
              mean over what exists, not zero-filled.
            </p>
          </MethodBlock>

          <MethodBlock title={m.coverage.name} what={m.coverage.what_it_is}
            formula={m.coverage.formula}>
            <ul className="method-areas">
              {m.coverage.areas.map((a) => <li key={a}>{a}</li>)}
            </ul>
          </MethodBlock>

          <MethodBlock title={m.axes.name} what={m.axes.what_it_is} formula={null}>
            <details className="method-rubric">
              <summary>First-pass kill screen — {m.axes.kill_screen.model}</summary>
              <pre>{m.axes.kill_screen.rubric}</pre>
            </details>
            {Object.entries(m.axes.rubrics).map(([axis, r]) => (
              <details key={axis} className="method-rubric">
                <summary>{axis} axis — {r.model}</summary>
                <pre>{r.rubric}</pre>
              </details>
            ))}
          </MethodBlock>

          <MethodBlock title={m.trust.name} what={m.trust.what_it_is} formula={null}>
            <table className="method-table">
              <thead><tr><th>tier</th><th>rubric trust</th><th>meaning</th></tr></thead>
              <tbody>
                {Object.entries(m.trust.rubric).map(([tier, val]) => (
                  <tr key={tier}>
                    <td>{tier.replace(/_/g, " ")}
                      {m.trust.contested_tiers.includes(tier) ? " *" : ""}</td>
                    <td className="it-num">{val.toFixed(2)}</td>
                    <td className="muted">{m.trust.tier_definitions[tier]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="method-note">
              * contested tiers (contradicted, self-reported) don't just take the
              rubric value — they go to a prosecutor → defender → judge debate
              whose verdict overrides it. Click any claim's trace on the
              Diligence page to see that debate for a specific claim.
            </p>
          </MethodBlock>
        </>
      )}
    </div>
  );
}

function MethodBlock({ title, what, formula, children }: {
  title: string; what: string; formula: string | null; children: ReactNode;
}) {
  return (
    <div className="block method-block">
      <h3>{title}</h3>
      <p className="method-what">{what}</p>
      {formula && <div className="it-formula">{formula}</div>}
      {children}
    </div>
  );
}
