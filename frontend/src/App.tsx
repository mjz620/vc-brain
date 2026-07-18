import { useEffect, useMemo, useState, ReactNode } from "react";
import * as api from "./api";
import type { Brief, Claim, FounderRow, Thesis } from "./api";

const TREND: Record<string, string> = {
  improving: "↑", declining: "↓", stable: "→", new: "✦",
};
function stanceClass(s?: string): string {
  if (!s) return "";
  if (/bullish|strong|survives|corroborated/i.test(s)) return "good";
  if (/bear|weak|contradicted/i.test(s)) return "bad";
  return "mid";
}

// --- click-to-evidence: render memo markdown with clickable [claim-id] citations ---
const CITE = /\[([a-z]{2,5}-\d{1,3})[^\]]*\]/g;

function renderInline(text: string, onCite: (id: string) => void): ReactNode[] {
  const nodes: ReactNode[] = [];
  let last = 0, m: RegExpExecArray | null, k = 0;
  CITE.lastIndex = 0;
  while ((m = CITE.exec(text))) {
    if (m.index > last) nodes.push(bold(text.slice(last, m.index), k++));
    const id = m[1];
    nodes.push(
      <button key={k++} className="cite" onClick={() => onCite(id)}>
        {m[0]}
      </button>,
    );
    last = m.index + m[0].length;
  }
  if (last < text.length) nodes.push(bold(text.slice(last), k++));
  return nodes;
}
function bold(t: string, key: number): ReactNode {
  const parts = t.split(/\*\*(.+?)\*\*/g);
  return (
    <span key={key}>
      {parts.map((p, i) => (i % 2 ? <strong key={i}>{p}</strong> : p))}
    </span>
  );
}
function Memo({ md, onCite }: { md: string; onCite: (id: string) => void }) {
  return (
    <div className="memo">
      {md.split("\n").map((line, i) => {
        const t = line.trimEnd();
        if (t.startsWith("## ")) return <h3 key={i}>{renderInline(t.slice(3), onCite)}</h3>;
        if (t.startsWith("# ")) return <h2 key={i}>{renderInline(t.slice(2), onCite)}</h2>;
        if (t.startsWith("- ")) return <li key={i}>{renderInline(t.slice(2), onCite)}</li>;
        if (!t) return <div key={i} className="sp" />;
        return <p key={i}>{renderInline(t, onCite)}</p>;
      })}
    </div>
  );
}

function AxisChips({ axes }: { axes: api.Axis[] }) {
  return (
    <div className="axes">
      {axes.map((a) =>
        a.status ? (
          <span key={a.axis} className="chip muted">{a.axis}: —</span>
        ) : (
          <span key={a.axis} className={`chip ${stanceClass(a.stance)}`}>
            {a.axis} {a.score}/10 {TREND[a.trend || "new"]}{" "}
            <em>{a.stance}</em> · cov {Math.round((a.coverage || 0) * 100)}%
          </span>
        ),
      )}
    </div>
  );
}

function EvidencePanel({ claim, onClose }: { claim: Claim | null; onClose: () => void }) {
  if (!claim) return null;
  return (
    <aside className="evidence">
      <button className="x" onClick={onClose}>×</button>
      <div className="ev-id">{claim.id} · {claim.axis}</div>
      <div className={`ev-tier ${stanceClass(claim.corroboration)}`}>
        trust {claim.trust.toFixed(2)} · {claim.corroboration} · {claim.stance}
      </div>
      <p className="ev-text">{claim.text}</p>
      <div className="ev-label">Evidence</div>
      <p className="ev-snip">{claim.evidence}</p>
      <a className="ev-src" href={claim.source_url} target="_blank" rel="noreferrer">
        {claim.source_type}: {claim.source_url}
      </a>
    </aside>
  );
}

function Detail({ brief, onBack }: { brief: Brief; onBack: () => void }) {
  const [active, setActive] = useState<Claim | null>(null);
  const byId = useMemo(
    () => Object.fromEntries(brief.claims.map((c) => [c.id, c])),
    [brief],
  );
  const rec = brief.recommendation || {};
  const lat = brief.latency;
  const onCite = (id: string) => setActive(byId[id] || null);
  return (
    <div className="detail">
      <button className="back" onClick={onBack}>← funnel</button>
      <div className="rec">
        <span className={`decision ${brief.decision || ""}`}>{brief.decision || "no memo"}</span>
        {rec.amount_usd ? <span> · ${rec.amount_usd.toLocaleString()}</span> : null}
        {rec.claims_it_turns_on?.length ? (
          <div className="turns">
            turns on:{" "}
            {rec.claims_it_turns_on.map((id) => (
              <button key={id} className="cite" onClick={() => onCite(id)}>[{id}]</button>
            ))}
          </div>
        ) : null}
        {rec.what_would_change_our_mind ? (
          <div className="wwcom"><b>What would change our mind:</b> {rec.what_would_change_our_mind}</div>
        ) : null}
      </div>

      <h4>Axes (independent — not averaged)</h4>
      <AxisChips axes={brief.axes} />

      <h4>Required fields (gaps flagged, never fabricated)</h4>
      <ul className="gaps">
        {brief.gaps.map((g) => (
          <li key={g.field} className={g.status === "gap" ? "gap" : "ok"}>
            {g.status === "gap" ? g.rendered : `${g.field}: disclosed ${g.claim_ids?.join(", ")}`}
          </li>
        ))}
      </ul>

      <h4>Latency: signal → decision</h4>
      <div className="strip">
        {lat.stages.map(([s, sec]) => (
          <span key={s} className="lat">{s} <b>{sec.toFixed(2)}s</b></span>
        ))}
        <span className="lat total">total <b>{lat.total_seconds.toFixed(2)}s</b></span>
      </div>

      <div className="memo-wrap">
        {brief.memo_md ? (
          <Memo md={brief.memo_md} onCite={onCite} />
        ) : (
          <p className="muted">No memo yet — run diligence on this founder.</p>
        )}
        <EvidencePanel claim={active} onClose={() => setActive(null)} />
      </div>
    </div>
  );
}

export default function App() {
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [thesis, setThesis] = useState("config/thesis_preseed_ai_infra.yaml");
  const [founders, setFounders] = useState<FounderRow[]>([]);
  const [killed, setKilled] = useState<{ id: string; reason: string }[]>([]);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<Brief | null>(null);

  useEffect(() => { api.getTheses().then(setTheses); api.getKilled().then(setKilled); }, []);
  useEffect(() => { api.getFounders(thesis).then(setFounders); }, [thesis]);

  const open = (id: string) => api.getFounder(id, thesis).then(setSelected);
  const shown = founders.filter((f) =>
    (f.name + f.source + f.axes.map((a) => a.stance).join(" ")).toLowerCase().includes(filter.toLowerCase()),
  );

  return (
    <div className="app">
      <header>
        <h1>VC Brain</h1>
        <span className="tag">evidence-first sourcing &amp; diligence</span>
        <select value={thesis} onChange={(e) => { setThesis(e.target.value); setSelected(null); }}>
          {theses.map((t) => <option key={t.file} value={t.file}>{t.name}</option>)}
        </select>
      </header>

      {selected ? (
        <Detail brief={selected} onBack={() => setSelected(null)} />
      ) : (
        <>
          <input className="filter" placeholder="filter founders (name / source / stance)…"
            value={filter} onChange={(e) => setFilter(e.target.value)} />
          <table className="funnel">
            <thead>
              <tr><th>Founder</th><th>Source</th><th>Signal / Coverage</th>
                <th>Founder</th><th>Market</th><th>Idea-vs-Market</th><th>Memo</th></tr>
            </thead>
            <tbody>
              {shown.map((f) => {
                const ax = Object.fromEntries(f.axes.map((a) => [a.axis, a]));
                return (
                  <tr key={f.id} onClick={() => open(f.id)}>
                    <td className="fname">{f.name}</td>
                    <td><span className="src">{f.source}</span></td>
                    <td><b>{f.signal}</b> · <span className="cov">{Math.round(f.coverage * 100)}%</span></td>
                    {["founder", "market", "idea"].map((k) => {
                      const a = ax[k];
                      return (
                        <td key={k} className={`axc ${stanceClass(a?.stance)}`}>
                          {a && a.score != null ? <>{a.score} {TREND[a.trend || "new"]}<em>{a.stance}</em></> : "—"}
                        </td>
                      );
                    })}
                    <td>{f.has_memo ? "📄" : ""}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {killed.length ? (
            <div className="killed">
              <h4>First-pass kill screen ({killed.length})</h4>
              {killed.map((k) => (
                <div key={k.id} className="kill"><b>{k.id}</b> — {k.reason}</div>
              ))}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
