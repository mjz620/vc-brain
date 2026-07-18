import { useEffect, useMemo, useState, ReactNode } from "react";
import * as api from "./api";
import type { Axis, Brief, Claim, FounderRow, Thesis } from "./api";

const TREND: Record<string, string> = { improving: "↑", declining: "↓", stable: "→", new: "✦" };
const AXES = ["founder", "market", "idea"] as const;
const AXLABEL: Record<string, string> = { founder: "Founder", market: "Market", idea: "Idea vs Mkt" };

function stanceClass(s?: string): string {
  if (!s) return "";
  if (/bullish|strong|survives|corroborated/i.test(s)) return "good";
  if (/bear|weak|contradicted/i.test(s)) return "bad";
  return "mid";
}
const isApplication = (f: FounderRow) => f.has_memo || f.source === "deck";

/* ---- theme ------------------------------------------------------------ */
function useTheme(): [string, () => void] {
  const [t, setT] = useState(
    () => localStorage.getItem("theme") ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  );
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", t);
    localStorage.setItem("theme", t);
  }, [t]);
  return [t, () => setT(t === "dark" ? "light" : "dark")];
}

/* ---- click-to-evidence memo ------------------------------------------- */
const CITE = /\[([a-z]{2,5}-\d{1,3})[^\]]*\]/g;
function inline(text: string, onCite: (id: string) => void): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0, m: RegExpExecArray | null, k = 0;
  CITE.lastIndex = 0;
  while ((m = CITE.exec(text))) {
    if (m.index > last) out.push(bold(text.slice(last, m.index), k++));
    const id = m[1];
    out.push(<button key={k++} className="cite" onClick={() => onCite(id)}>{m[0]}</button>);
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(bold(text.slice(last), k++));
  return out;
}
function bold(t: string, key: number): ReactNode {
  const parts = t.split(/\*\*(.+?)\*\*/g);
  return <span key={key}>{parts.map((p, i) => (i % 2 ? <strong key={i}>{p}</strong> : p))}</span>;
}
// drop the memo's own "## Recommendation" block — the recommendation card covers it
function stripRecommendation(md: string): string {
  return md.replace(/##\s*Recommendation[\s\S]*?(?=\n##\s|\n#\s|$)/i, "").trim();
}
function Memo({ md, onCite }: { md: string; onCite: (id: string) => void }) {
  return (
    <div className="memo">
      {stripRecommendation(md).split("\n").map((line, i) => {
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
function Evidence({ claim, onClose }: { claim: Claim | null; onClose: () => void }) {
  if (!claim) return null;
  return (
    <aside className="evidence">
      <button className="x" onClick={onClose}>×</button>
      <div className="ev-id">{claim.id}</div>
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

/* ---- detail ----------------------------------------------------------- */
function Detail({ brief, onBack }: { brief: Brief; onBack: () => void }) {
  const [active, setActive] = useState<Claim | null>(null);
  const byId = useMemo(() => Object.fromEntries(brief.claims.map((c) => [c.id, c])), [brief]);
  const onCite = (id: string) => setActive(byId[id] || null);
  const rec = brief.recommendation || {};
  const d = brief.decision || "none";
  const axById = Object.fromEntries(brief.axes.map((a) => [a.axis, a]));

  return (
    <div>
      <button className="back" onClick={onBack}>← back to funnel</button>
      <div className="rec-card">
        <div className="head">
          <span className={`badge ${d}`}>{d}</span>
          <h1>{brief.founder_id.replace("founder-", "")}</h1>
          {rec.amount_usd ? <span className="amt"><b>${rec.amount_usd.toLocaleString()}</b> check</span> : null}
        </div>
        {rec.claims_it_turns_on?.length ? (
          <div className="turns">turns on
            {rec.claims_it_turns_on.map((id) => (
              <button key={id} className="cite" onClick={() => onCite(id)}>[{id}]</button>
            ))}
          </div>
        ) : null}
        {rec.what_would_change_our_mind ? (
          <div className="wwcom"><b>What would change our mind:</b> {rec.what_would_change_our_mind}</div>
        ) : null}
      </div>

      <div className="subgrid">
        <div className="block">
          <h3>Axes — independent, never averaged</h3>
          <div className="axes">
            {AXES.map((k) => {
              const a: Axis | undefined = axById[k];
              const sc = a && a.score != null ? a.score : 0;
              return (
                <div className="axline" key={k}>
                  <span className="lbl">{AXLABEL[k]}</span>
                  <span className="bar"><span className={stanceClass(a?.stance)} style={{ width: `${sc * 10}%` }} /></span>
                  <span className="num">
                    {a && a.score != null ? <>{a.score} {TREND[a.trend || "new"]} <em>{a.stance}</em></> : "—"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
        <div className="block">
          <h3>Required fields — gaps flagged, never fabricated</h3>
          <ul className="gaps">
            {brief.gaps.map((g) => (
              <li key={g.field} className={g.status === "gap" ? "gap" : "ok"}>
                {g.status === "gap" ? g.rendered : `${g.field}: disclosed`}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="block" style={{ marginBottom: 18 }}>
        <h3>Latency — first signal → decision</h3>
        <div className="strip">
          {brief.latency.stages.map(([s, sec]) => (
            <span key={s} className="lat">{s} <b>{sec.toFixed(2)}s</b></span>
          ))}
          <span className="lat total">total <b>{brief.latency.total_seconds.toFixed(2)}s</b></span>
        </div>
      </div>

      {brief.memo_md ? (
        <div className="memo-wrap">
          <Memo md={brief.memo_md} onCite={onCite} />
          <Evidence claim={active} onClose={() => setActive(null)} />
        </div>
      ) : (
        <p className="muted">No memo yet — this founder was sourced but not put through full diligence.</p>
      )}
    </div>
  );
}

/* ---- dashboard pieces ------------------------------------------------- */
function AppCard({ f, onOpen }: { f: FounderRow; onOpen: () => void }) {
  const ax = Object.fromEntries(f.axes.map((a) => [a.axis, a]));
  return (
    <div className="card" onClick={onOpen}>
      <div className="top">
        <span className="name">{f.name}</span>
        <span className="pill">{f.source === "deck" ? "inbound" : f.source}</span>
        <span className="sc"><b>{f.signal}</b> signal · {Math.round(f.coverage * 100)}% cov</span>
      </div>
      <div className="axrow">
        {AXES.map((k) => {
          const a = ax[k];
          return (
            <div key={k} className={`axcell ${stanceClass(a?.stance)}`}>
              <div className="k">{AXLABEL[k]}</div>
              <div className="v">
                {a && a.score != null ? <>{a.score}<small>{TREND[a.trend || "new"]} {a.stance}</small></> : "—"}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function App() {
  const [theme, toggle] = useTheme();
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [thesis, setThesis] = useState("config/thesis_preseed_ai_infra.yaml");
  const [founders, setFounders] = useState<FounderRow[]>([]);
  const [killed, setKilled] = useState<{ id: string; reason: string }[]>([]);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<Brief | null>(null);

  useEffect(() => { api.getTheses().then(setTheses); api.getKilled().then(setKilled); }, []);
  useEffect(() => { api.getFounders(thesis).then(setFounders); }, [thesis]);
  const open = (id: string) => api.getFounder(id, thesis).then(setSelected);

  const apps = founders.filter(isApplication);
  const sourced = founders.filter((f) => !isApplication(f)).filter((f) =>
    (f.name + f.source + f.axes.map((a) => a.stance).join(" ")).toLowerCase().includes(filter.toLowerCase()));

  return (
    <div className="app">
      <header>
        <span className="brand">VC Brain<span className="dot">.</span></span>
        <span className="subtitle">evidence-first sourcing &amp; diligence</span>
        <span className="spacer" />
        <select className="control" value={thesis}
          onChange={(e) => { setThesis(e.target.value); setSelected(null); }}>
          {theses.map((t) => <option key={t.file} value={t.file}>{t.name}</option>)}
        </select>
        <button className="control" onClick={toggle} title="toggle theme">
          {theme === "dark" ? "☀" : "☾"}
        </button>
      </header>

      {selected ? (
        <Detail brief={selected} onBack={() => setSelected(null)} />
      ) : (
        <>
          {apps.length ? (
            <>
              <div className="section-h"><h2>Applications</h2>
                <span className="count">{apps.length} in diligence</span></div>
              <div className="apps">
                {apps.map((f) => <AppCard key={f.id} f={f} onOpen={() => open(f.id)} />)}
              </div>
            </>
          ) : null}

          <div className="section-h"><h2>Sourced funnel</h2>
            <span className="count">{sourced.length} scanned &amp; screened</span></div>
          <input className="filter" placeholder="filter by name / source / stance…"
            value={filter} onChange={(e) => setFilter(e.target.value)} />
          <table className="funnel">
            <thead>
              <tr><th>Founder</th><th>Source</th><th>Signal / Cov</th>
                <th>Founder</th><th>Market</th><th>Idea vs Mkt</th></tr>
            </thead>
            <tbody>
              {sourced.map((f) => {
                const ax = Object.fromEntries(f.axes.map((a) => [a.axis, a]));
                return (
                  <tr key={f.id} onClick={() => open(f.id)}>
                    <td className="fname">{f.name}</td>
                    <td><span className="src">{f.source}</span></td>
                    <td><b>{f.signal}</b> · <span className="cov">{Math.round(f.coverage * 100)}%</span></td>
                    {AXES.map((k) => {
                      const a = ax[k];
                      return (
                        <td key={k} className={`axmini ${stanceClass(a?.stance)}`}>
                          {a && a.score != null ? <>{a.score} {TREND[a.trend || "new"]}<em>{a.stance}</em></> : "—"}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>

          {killed.length ? (
            <div className="killed">
              <div className="section-h"><h2>First-pass kill screen</h2>
                <span className="count">{killed.length} removed before diligence</span></div>
              {killed.map((k) => (
                <div key={k.id} className="kill"><b>{k.id.replace("founder-", "")}</b> — {k.reason}</div>
              ))}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
