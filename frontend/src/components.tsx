import { ReactNode, useEffect, useState } from "react";
import * as api from "./api";
import type { Trace } from "./api";

export const TREND: Record<string, string> = { improving: "↑", declining: "↓", stable: "→", new: "✦" };
export const AXES = ["founder", "market", "idea"] as const;
export const AXLABEL: Record<string, string> = { founder: "Founder", market: "Market", idea: "Idea vs Mkt" };

export function stanceClass(s?: string): string {
  if (!s) return "";
  if (/bullish|strong|survives|corroborated/i.test(s)) return "good";
  if (/bear|weak|contradicted/i.test(s)) return "bad";
  return "mid";
}
/* one tier color language, used identically on every page */
export function tierClass(t?: string): string {
  if (!t) return "";
  if (t === "corroborated") return "tier-corr";
  if (t === "single_source") return "tier-single";
  if (t === "self_reported") return "tier-self";
  if (t === "contradicted") return "tier-contra";
  return "tier-inferred";
}
export const TIER_SHORT: Record<string, string> = {
  corroborated: "corr", single_source: "single", self_reported: "self",
  contradicted: "CONTRA", inferred: "inferred",
};
export function TierChip({ tier, trust }: { tier: string; trust?: number }) {
  return (
    <span className={`tierchip ${tierClass(tier)}`}>
      {trust != null ? `${trust.toFixed(2)} · ` : ""}{TIER_SHORT[tier] || tier}
    </span>
  );
}

/* ---- click-to-evidence memo (multi-id brackets become one chip per id) --- */
const BRACKET = /\[([^\]]*\b[a-z]{2,5}-\d{1,3}\b[^\]]*)\]/g;
const ID = /\b([a-z]{2,5}-\d{1,3})\b/g;
export function inline(text: string, onCite: (id: string) => void): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0, m: RegExpExecArray | null, k = 0;
  BRACKET.lastIndex = 0;
  while ((m = BRACKET.exec(text))) {
    if (m.index > last) out.push(bold(text.slice(last, m.index), k++));
    const ids = [...m[1].matchAll(ID)].map((x) => x[1]);
    const segs = m[1].split(";");
    out.push(
      <span key={k++} className="citegroup">
        {ids.map((id, i) => (
          <button key={id + i} className="cite" onClick={() => onCite(id)}>
            [{(segs[i] || id).trim()}]
          </button>
        ))}
      </span>,
    );
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(bold(text.slice(last), k++));
  return out;
}
function bold(t: string, key: number): ReactNode {
  const parts = t.split(/\*\*(.+?)\*\*/g);
  return <span key={key}>{parts.map((p, i) => (i % 2 ? <strong key={i}>{p}</strong> : p))}</span>;
}

export function Memo({ md, onCite }: { md: string; onCite: (id: string) => void }) {
  return (
    <div className="memo">
      {md.split("\n").map((line, i) => {
        const t = line.trimEnd();
        if (t.startsWith("## ")) return <h2 key={i}>{inline(t.slice(3), onCite)}</h2>;
        if (t.startsWith("# ")) return <h2 key={i}>{inline(t.slice(2), onCite)}</h2>;
        if (t.startsWith("### ")) return <h3 key={i}>{inline(t.slice(4), onCite)}</h3>;
        if (t.startsWith("- ")) return <li key={i}>{inline(t.slice(2), onCite)}</li>;
        if (!t) return <div key={i} className="sp" />;
        return <p key={i}>{inline(t, onCite)}</p>;
      })}
    </div>
  );
}

/* ---- the trace panel: claim -> evidence -> signal -> how trust was set --- */
export function TracePanel({ founderId, claimId, onClose }:
  { founderId: string; claimId: string; onClose: () => void }) {
  const [trace, setTrace] = useState<Trace | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [showDebate, setShowDebate] = useState(false);
  useEffect(() => {
    setTrace(null); setErr(null); setShowDebate(false);
    api.getTrace(founderId, claimId).then(setTrace).catch((e) => setErr(e.message));
  }, [founderId, claimId]);

  return (
    <aside className="evidence trace">
      <button className="x" onClick={onClose}>×</button>
      {err && <Err msg={err} />}
      {!trace && !err && <Skeleton lines={6} />}
      {trace && (
        <>
          <div className="ev-id">{trace.claim.id}</div>
          <div style={{ margin: "4px 0 10px" }}>
            <TierChip tier={trace.claim.corroboration} trust={trace.claim.trust} />
            <span className="muted" style={{ fontSize: 12, marginLeft: 6 }}>{trace.claim.stance}</span>
          </div>
          <p className="ev-text">{trace.claim.text}</p>

          <div className="ev-label">Evidence</div>
          <p className="ev-snip">{trace.claim.evidence}</p>

          <div className="ev-label">Source signal{trace.signals.length === 1 ? "" : "s"}</div>
          {trace.signals.length === 0 && (
            <p className="ev-snip">
              no raw signal on record —{" "}
              <a href={trace.claim.source_url} target="_blank" rel="noreferrer">source link</a>
            </p>
          )}
          {trace.signals.map((s) => (
            <div key={s.id} className="tr-signal">
              <span className="src">{s.source}</span>
              <span className="tr-date">{(s.observed_at || s.ingested_at).slice(0, 10)}</span>
              <p className="ev-snip">{s.content.length > 220 ? s.content.slice(0, 220) + "…" : s.content}</p>
              <a className="ev-src" href={s.source_url} target="_blank" rel="noreferrer">{s.source_url}</a>
            </div>
          ))}

          <div className="ev-label">How trust was set</div>
          {trace.adjudication ? (
            <div className="tr-adj">
              <p className="ev-snip">
                rubric <s>{trace.rubric_trust.toFixed(2)}</s> → judge{" "}
                <b>{trace.adjudication.trust.toFixed(2)}</b>{" "}
                <TierChip tier={trace.adjudication.corroboration} />
              </p>
              <p className="ev-snip"><em>{trace.adjudication.rationale}</em></p>
              <button className="linkbtn" onClick={() => setShowDebate(!showDebate)}>
                {showDebate ? "hide" : "show"} prosecutor / defender transcript
              </button>
              {showDebate && (
                <div className="transcript">
                  <div className="t-role bad">Prosecutor</div>
                  <p>{trace.adjudication.prosecution}</p>
                  <div className="t-role good">Defender</div>
                  <p>{trace.adjudication.defense}</p>
                  <div className="t-role">Judge</div>
                  <p>{trace.adjudication.rationale}</p>
                </div>
              )}
            </div>
          ) : (
            <p className="ev-snip">
              rubric-anchored: tier "{trace.claim.corroboration}" → trust {trace.claim.trust.toFixed(2)}
              {" "}(uncontested — no adjudication needed)
            </p>
          )}
        </>
      )}
    </aside>
  );
}

/* ---- loading / error --------------------------------------------------- */
export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="skeleton">
      {Array.from({ length: lines }, (_, i) => <div key={i} className="sk-line" />)}
    </div>
  );
}
export function Err({ msg }: { msg: string }) {
  return <div className="err">⚠ {msg}</div>;
}
