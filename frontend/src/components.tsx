import { ReactNode, useEffect, useRef, useState } from "react";
import * as api from "./api";
import type { Methodology, ScorePoint, Trace } from "./api";

export const TREND: Record<string, string> = { improving: "↑", declining: "↓", stable: "→", new: "✦" };
/* A screen reader announces a bare Unicode arrow as "upwards arrow", not "improving" —
   wrap every TREND glyph render in this so the word is always available to AT. */
export function TrendGlyph({ trend }: { trend?: string }) {
  const t = trend || "new";
  return <span aria-label={t}>{TREND[t]}</span>;
}
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

/* ---- InfoTip: "how is this computed" — the real formula, sourced live from
   the backend's own constants, never a hand-typed paraphrase that could drift. */
type InfoKind = "signal" | "coverage" | "axis" | "trust";
export function InfoTip({ kind, axis, founderId }: {
  kind: InfoKind; axis?: string; founderId?: string;
}) {
  const [open, setOpen] = useState(false);
  const [m, setM] = useState<Methodology | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (open && !m && !err) {
      api.getMethodology(founderId).then(setM).catch((e) => setErr(e.message));
    }
  }, [open, founderId, m, err]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <span className="infotip" ref={ref}>
      <button type="button" className="infotip-btn"
        aria-label={`how is ${axis || kind} computed`} aria-expanded={open}
        onClick={(e) => { e.stopPropagation(); e.preventDefault(); setOpen((v) => !v); }}>
        ⓘ
      </button>
      {open && (
        <div className="infotip-pop" role="dialog" aria-label="scoring methodology"
          onClick={(e) => e.stopPropagation()}>
          {err && <Err msg={err} />}
          {!m && !err && <Skeleton lines={3} />}
          {m && <InfoTipBody kind={kind} axis={axis} m={m} />}
        </div>
      )}
    </span>
  );
}

function InfoTipBody({ kind, axis, m }: { kind: InfoKind; axis?: string; m: Methodology }) {
  const forFounder = m.for_founder;
  if (kind === "signal") {
    const sig = m.signal;
    const fd = forFounder?.signal.dimensions;
    return (
      <>
        <div className="it-h">{sig.name}</div>
        <p className="it-p">{sig.what_it_is}</p>
        <div className="it-formula">{sig.formula}</div>
        {fd ? (
          <table className="it-table">
            <tbody>
              {fd.map((d) => (
                <tr key={d.name} className={d.assessed ? "" : "muted"}>
                  <td>{d.name.replace(/_/g, " ")}</td>
                  <td className="it-num">{d.assessed ? d.value : "unassessed"}</td>
                  <td className="it-num">{d.assessed ? `×${d.renormalized_weight}` : `w=${d.weight}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <table className="it-table">
            <tbody>
              {Object.entries(sig.dimensions).map(([k, desc]) => (
                <tr key={k}>
                  <td>{k.replace(/_/g, " ")} <em>w={sig.weights[k]}</em></td>
                  <td className="it-desc">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {fd && (
          <div className="it-note">
            these are THIS founder's actual numbers — click a founder's page for the
            per-dimension derivation shown here inline.
          </div>
        )}
      </>
    );
  }
  if (kind === "coverage") {
    const cov = m.coverage;
    const areas = forFounder?.coverage.areas;
    return (
      <>
        <div className="it-h">{cov.name}</div>
        <p className="it-p">{cov.what_it_is}</p>
        <div className="it-formula">{cov.formula}</div>
        <ul className="it-areas">
          {(areas || cov.areas.map((a) => ({ area: a, covered: undefined }))).map((a) => (
            <li key={a.area} className={a.covered === undefined ? "" : a.covered ? "good" : "bad"}>
              {a.covered === true ? "✓ " : a.covered === false ? "✗ " : "· "}{a.area}
            </li>
          ))}
        </ul>
      </>
    );
  }
  if (kind === "trust") {
    const t = m.trust;
    return (
      <>
        <div className="it-h">{t.name}</div>
        <p className="it-p">{t.what_it_is}</p>
        <table className="it-table">
          <tbody>
            {Object.entries(t.rubric).map(([tier, val]) => (
              <tr key={tier} className={t.contested_tiers.includes(tier) ? "" : "muted"}>
                <td>{tier.replace(/_/g, " ")}{t.contested_tiers.includes(tier) ? " *" : ""}</td>
                <td className="it-num">{val.toFixed(2)}</td>
                <td className="it-desc">{t.tier_definitions[tier]}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="it-note">* contested tiers go to a prosecutor→defender→judge
          debate whose verdict overrides this rubric value.</div>
      </>
    );
  }
  // axis
  const ax = m.axes;
  const rub = axis ? ax.rubrics[axis] : null;
  return (
    <>
      <div className="it-h">{AXLABEL[axis || ""] || ax.name} axis</div>
      <p className="it-p">{ax.what_it_is}</p>
      {rub && (
        <>
          <div className="it-note">scored by {rub.model} against this rubric:</div>
          <pre className="it-rubric">{rub.rubric}</pre>
        </>
      )}
    </>
  );
}

/* ---- Signal / Coverage: TWO meters, deliberately never one number -------- */
export function Meters({ signal, coverage, founderId }: {
  signal: number | null; coverage: number; founderId?: string;
}) {
  return (
    <div className="meters">
      <div className="meter" title="Signal: verified-evidence Founder Score (0–10)">
        <span className="m-k">Signal <InfoTip kind="signal" founderId={founderId} /></span>
        <span className="m-bar"><span style={{ width: `${((signal ?? 0) / 10) * 100}%` }} /></span>
        <span className="m-v">{signal ?? "—"}<em>/10</em></span>
      </div>
      <div className="meter cov" title="Coverage: how complete the record is (0–100%)">
        <span className="m-k">Coverage <InfoTip kind="coverage" founderId={founderId} /></span>
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
        if (t.startsWith("- ") || t.startsWith("* "))
          return <li key={i}>{inline(t.slice(2), onCite)}</li>;
        const ol = t.match(/^(\d{1,2})\.\s+(.*)/);  // ordered list: "1. …"
        if (ol) return <div key={i} className="memo-oli"><b>{ol[1]}.</b> {inline(ol[2], onCite)}</div>;
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
  const panelRef = useRef<HTMLElement>(null);
  useEffect(() => {
    setTrace(null); setErr(null); setShowDebate(false);
    api.getTraceCached(founderId, claimId).then(setTrace).catch((e) => setErr(e.message));
    // On narrow screens the rail stacks out of view; bring it to the user on open.
    // scrollIntoView's own `behavior` option ignores the CSS reduced-motion override,
    // so it's gated here explicitly.
    if (window.innerWidth <= 860) {
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      panelRef.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    }
  }, [founderId, claimId]);
  // Esc closes the evidence rail — a keyboard exit from the panel.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <aside className="evidence trace" role="complementary" aria-label="Evidence trace" ref={panelRef}>
      <button className="x" onClick={onClose} aria-label="Close evidence panel"
        title="Close (Esc)">×</button>
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

          <div className="ev-label">How trust was set <InfoTip kind="trust" /></div>
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
  // Exact match — decision is the invest|pass|conditional enum, not free text.
  const decClass = ["invest", "pass", "conditional"].includes(decision) ? decision : "none";

  return (
    <div className="prov">
      <svg viewBox={`0 0 ${W} ${H}`} role="group"
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
            role="button" tabIndex={0}
            aria-label={`${c.id}, ${c.corroboration} — open full trace`}
            onMouseEnter={() => setHover({ kind: "claim", key: c.id })}
            onMouseLeave={() => setHover(null)}
            onFocus={() => setHover({ kind: "claim", key: c.id })}
            onBlur={() => setHover(null)}
            onClick={() => onOpenClaim(c.id)}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpenClaim(c.id); } }}>
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
