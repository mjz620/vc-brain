import { ReactNode, useEffect, useState } from "react";
import * as api from "./api";
import type { ScorePoint, Trace } from "./api";

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

/* ---- evidence source identity ------------------------------------------ */
/* file:// and application:// (pitch-deck) URLs are records, not links —
   they must never render as dead <a> tags. */
export function sourceDomain(url?: string | null): { label: string; href: string | null } {
  if (!url) return { label: "no source url", href: null };
  if (url.startsWith("file://") || url.startsWith("application://"))
    return { label: "pitch deck", href: null };
  try {
    return { label: new URL(url).hostname.replace(/^www\./, ""), href: url };
  } catch {
    return { label: url, href: null };
  }
}
export function DomainChip({ url }: { url?: string | null }) {
  const d = sourceDomain(url);
  return d.href
    ? <a className="domchip" href={d.href} target="_blank" rel="noreferrer">{d.label}</a>
    : <span className="domchip deck">{d.label}</span>;
}

/* ---- Founder Score sparkline (inline SVG, no library) -------------------- */
/* One point renders a flat tick — never a fake trend. Tooltip = trigger + date. */
export function Sparkline({ history, width = 96, height = 26 }:
  { history: ScorePoint[]; width?: number; height?: number }) {
  if (!history?.length) return null;
  const pad = 4;
  const tip = (p: ScorePoint) => `${p.trigger} · ${p.timestamp.slice(0, 10)} · score ${p.score}`;
  if (history.length === 1) {
    return (
      <svg className="spark" width={width} height={height} viewBox={`0 0 ${width} ${height}`}
        role="img" aria-label="score history: one point on record">
        <title>{tip(history[0])}</title>
        <line x1={width / 2 - 8} x2={width / 2 + 8} y1={height / 2} y2={height / 2} />
        <circle cx={width / 2} cy={height / 2} r={2.5} />
      </svg>
    );
  }
  const scores = history.map((h) => h.score);
  const min = Math.min(...scores), max = Math.max(...scores);
  const span = max - min || 1;
  const x = (i: number) => pad + (i * (width - 2 * pad)) / (history.length - 1);
  const y = (s: number) => height - pad - ((s - min) / span) * (height - 2 * pad);
  return (
    <svg className="spark" width={width} height={height} viewBox={`0 0 ${width} ${height}`}
      role="img" aria-label={`score history, ${history.length} points`}>
      <polyline points={history.map((h, i) => `${x(i)},${y(h.score)}`).join(" ")} />
      {history.map((h, i) => (
        <circle key={i} cx={x(i)} cy={y(h.score)} r={2.5}>
          <title>{tip(h)}</title>
        </circle>
      ))}
    </svg>
  );
}

/* ---- Signal / Coverage: TWO meters, deliberately never one number -------- */
export function Meters({ signal, coverage }: { signal: number | null; coverage: number }) {
  return (
    <div className="meters">
      <div className="meter" title="Signal: verified-evidence Founder Score (0–10)">
        <span className="m-k">Signal</span>
        <span className="m-bar"><span style={{ width: `${((signal ?? 0) / 10) * 100}%` }} /></span>
        <span className="m-v">{signal ?? "—"}<em>/10</em></span>
      </div>
      <div className="meter cov" title="Coverage: how complete the record is (0–100%)">
        <span className="m-k">Coverage</span>
        <span className="m-bar"><span style={{ width: `${Math.round(coverage * 100)}%` }} /></span>
        <span className="m-v">{Math.round(coverage * 100)}<em>%</em></span>
      </div>
    </div>
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
    api.getTraceCached(founderId, claimId).then(setTrace).catch((e) => setErr(e.message));
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
          <div className="srccard">
            <div className="src-top">
              <DomainChip url={trace.claim.evidence_url} />
              {trace.claim.retrieved_at && (
                <span className="src-date">retrieved {trace.claim.retrieved_at.slice(0, 10)}</span>
              )}
            </div>
            {trace.claim.evidence_title && (
              <div className="src-title">{trace.claim.evidence_title}</div>
            )}
            {trace.claim.evidence_excerpt
              ? <blockquote className="src-quote">“{trace.claim.evidence_excerpt}”</blockquote>
              : <p className="ev-snip" style={{ margin: "6px 0 0" }}>{trace.claim.evidence}</p>}
          </div>

          <div className="ev-label">Source signal{trace.signals.length === 1 ? "" : "s"}</div>
          {trace.signals.length === 0 && (
            <p className="ev-snip">
              no raw signal on record — the source card above is the whole provenance
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

/* ---- evidence provenance graph (pure inline SVG, no library) -------------
   decision → the claims the recommendation turns on (tier-colored) → the
   evidence domains they rest on. Hover highlights a chain; click a claim
   opens its full trace. Contradicted claims are always shown. */
export function ProvenanceGraph({ decision, turnsOn, claims, totalClaims, onOpenClaim }: {
  decision: string;
  turnsOn: string[];
  claims: { id: string; text: string; corroboration: string; evidence_url: string }[];
  totalClaims: number;
  onOpenClaim: (id: string) => void;
}) {
  const [hover, setHover] = useState<{ kind: "claim" | "domain"; key: string } | null>(null);
  const byId = new Map(claims.map((c) => [c.id, c]));
  let shown = turnsOn.map((id) => byId.get(id)).filter((c): c is NonNullable<typeof c> => !!c);
  const shownIds = new Set(shown.map((c) => c.id));
  for (const c of claims) {
    if (c.corroboration === "contradicted" && !shownIds.has(c.id)) {
      shown.push(c); shownIds.add(c.id);
    }
  }
  if (shown.length > 12) shown = shown.slice(0, 12);
  const more = totalClaims - shown.length;

  const domains = [...new Set(shown.map((c) => sourceDomain(c.evidence_url).label))];
  const domY = new Map(domains.map((d, i) => [d, i]));
  const ROW = 36, W = 720, PAD = 10;
  const rows = Math.max(shown.length, domains.length, 1);
  const H = rows * ROW + PAD * 2 + (more > 0 ? 18 : 0);
  const cy = (i: number, n: number) => PAD + ((rows - n) * ROW) / 2 + i * ROW + 12;
  const decY = cy(0, 1) + ((rows - 1) * ROW) / 2;
  const bez = (x1: number, y1: number, x2: number, y2: number) => {
    const mx = (x1 + x2) / 2;
    return `M${x1} ${y1} C${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
  };
  const activeClaims: Set<string> = !hover ? new Set()
    : hover.kind === "claim" ? new Set([hover.key])
    : new Set(shown.filter((c) => sourceDomain(c.evidence_url).label === hover.key).map((c) => c.id));
  const activeDomains = new Set(
    [...activeClaims].map((id) => sourceDomain(byId.get(id)?.evidence_url).label));
  const dim = (on: boolean) => (hover && !on ? " dim" : "");
  const decClass = decision.includes("pass") ? "pass"
    : decision.includes("conditional") ? "conditional"
    : decision.includes("invest") ? "invest" : "none";

  return (
    <div className="prov">
      <svg viewBox={`0 0 ${W} ${H}`} role="img"
        aria-label="provenance: decision to claims to evidence domains">
        {shown.map((c, i) => (
          <path key={`e1-${c.id}`}
            className={`edge${hover && activeClaims.has(c.id) ? " hot" : ""}${dim(activeClaims.has(c.id))}`}
            d={bez(148, decY, 280, cy(i, shown.length))} />
        ))}
        {shown.map((c, i) => {
          const d = sourceDomain(c.evidence_url).label;
          const j = domY.get(d) ?? 0;
          return (
            <path key={`e2-${c.id}`}
              className={`edge${hover && activeClaims.has(c.id) ? " hot" : ""}${dim(activeClaims.has(c.id))}`}
              d={bez(432, cy(i, shown.length), 530, cy(j, domains.length))} />
          );
        })}
        <g className={`dec-node dec-${decClass}${dim(true)}`}>
          <rect x={8} y={decY - 14} width={140} height={28} rx={7} />
          <text x={78} y={decY + 4} textAnchor="middle">{decision}</text>
        </g>
        {shown.map((c, i) => (
          <g key={c.id} className={`pnode ${tierClass(c.corroboration)}${dim(activeClaims.has(c.id))}`}
            onMouseEnter={() => setHover({ kind: "claim", key: c.id })}
            onMouseLeave={() => setHover(null)}
            onClick={() => onOpenClaim(c.id)}>
            <title>{`${c.id} (${c.corroboration}) — ${c.text} · click for full trace`}</title>
            <rect x={280} y={cy(i, shown.length) - 12} width={152} height={24} rx={6} />
            <text x={292} y={cy(i, shown.length) + 4}>{c.id} · {TIER_SHORT[c.corroboration] || c.corroboration}</text>
          </g>
        ))}
        {domains.map((d, j) => (
          <g key={d} className={`dnode${dim(activeDomains.has(d))}`}
            onMouseEnter={() => setHover({ kind: "domain", key: d })}
            onMouseLeave={() => setHover(null)}>
            <rect x={530} y={cy(j, domains.length) - 12} width={182} height={24} rx={6} />
            <text x={541} y={cy(j, domains.length) + 4}>
              {d.length > 26 ? d.slice(0, 25) + "…" : d}
            </text>
          </g>
        ))}
        {more > 0 && (
          <text className="prov-more" x={280} y={H - 6}>+{more} more claims in the ledger</text>
        )}
      </svg>
    </div>
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

/* Persistent founder switcher (page header): lateral movement at any time —
   never a dead end. Empty option resets to the picker. */
export function FounderSwitcher({ founderId, founders, openFounder }: {
  founderId: string | null;
  founders: { id: string; name: string }[];
  openFounder: (id: string) => void;
}) {
  return (
    <select className="control" value={founderId ?? ""}
      onChange={(e) => openFounder(e.target.value)} title="switch founder">
      <option value="">all founders…</option>
      {founderId && !founders.some((f) => f.id === founderId) && (
        <option value={founderId}>{founderId.replace("founder-", "")}</option>
      )}
      {founders.map((f) => (
        <option key={f.id} value={f.id}>{f.name}</option>
      ))}
    </select>
  );
}
