import { useState } from "react";
import * as api from "../api";
import type { QueryResult, Thesis } from "../api";
import { Err } from "../components";

/* Page 5 — "Same data, different fund, different answer."
   Editable thesis config + the NL multi-attribute query with honest criterion chips. */
export default function ThesisPage({ theses, thesis, setThesis, refreshTheses, openFounder }: {
  theses: Thesis[]; thesis: string; setThesis: (t: string) => void;
  refreshTheses: () => void; openFounder: (id: string) => void;
}) {
  return (
    <div>
      <div className="page-h">
        <h1>Thesis &amp; Query</h1>
        <p className="page-sub">
          The Thesis Engine is configurable — sectors, stage, geography, check size,
          ownership, risk appetite — and every scan, screen, and recommendation runs
          through the selected lens. Swap it and the answers change; the data doesn't.
        </p>
      </div>

      <div className="twocol">
        <div>
          <div className="section-h"><h2>Active thesis</h2></div>
          <div className="picker" style={{ marginBottom: 16 }}>
            {theses.map((t) => (
              <button key={t.file}
                className={`minibtn ${t.file === thesis ? "primary" : ""}`}
                onClick={() => setThesis(t.file)}>{t.name}</button>
            ))}
          </div>
          <ThesisEditor onSaved={(file) => { refreshTheses(); setThesis(file); }} />
        </div>
        <div>
          <div className="section-h"><h2>Multi-attribute query</h2></div>
          <QueryBox openFounder={openFounder} />
        </div>
      </div>
    </div>
  );
}

function ThesisEditor({ onSaved }: { onSaved: (file: string) => void }) {
  const [cfg, setCfg] = useState({
    name: "My Fund", sectors: "ai-infra, developer-tools", stage: "pre-seed",
    geography: "US, EU, remote", check_size_usd: 100000, ownership_target_pct: 8,
    risk_appetite: "high", topics: "llm, agents, evaluation",
  });
  const [state, setState] = useState<string | null>(null);
  const set = (k: string, v: string | number) => setCfg({ ...cfg, [k]: v });
  const save = async () => {
    setState("saving…");
    try {
      const list = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
      const t = await api.saveThesis({
        ...cfg, sectors: list(cfg.sectors), geography: list(cfg.geography),
        topics: list(cfg.topics),
        check_size_usd: Number(cfg.check_size_usd),
        ownership_target_pct: Number(cfg.ownership_target_pct),
      });
      setState(`saved ${t.file}`);
      onSaved(t.file);
    } catch (e) {
      setState(`⚠ ${(e as Error).message}`);
    }
  };
  return (
    <div className="block">
      <h3>New thesis config</h3>
      <div className="t-grid">
        <label>Name<input className="filter" value={cfg.name} onChange={(e) => set("name", e.target.value)} /></label>
        <label>Stage<input className="filter" value={cfg.stage} onChange={(e) => set("stage", e.target.value)} /></label>
        <label>Sectors<input className="filter" value={cfg.sectors} onChange={(e) => set("sectors", e.target.value)} /></label>
        <label>Geography<input className="filter" value={cfg.geography} onChange={(e) => set("geography", e.target.value)} /></label>
        <label>Check size $<input className="filter" type="number" value={cfg.check_size_usd} onChange={(e) => set("check_size_usd", e.target.value)} /></label>
        <label>Ownership %<input className="filter" type="number" value={cfg.ownership_target_pct} onChange={(e) => set("ownership_target_pct", e.target.value)} /></label>
        <label>Risk appetite
          <select className="filter" value={cfg.risk_appetite} onChange={(e) => set("risk_appetite", e.target.value)}>
            <option>high</option><option>medium</option><option>low</option>
          </select>
        </label>
        <label>Scan topics<input className="filter" value={cfg.topics} onChange={(e) => set("topics", e.target.value)} /></label>
      </div>
      <button className="minibtn primary" onClick={save}>Save thesis</button>
      {state && <span className="muted" style={{ marginLeft: 10, fontSize: 12.5 }}>{state}</span>}
    </div>
  );
}

function QueryBox({ openFounder }: { openFounder: (id: string) => void }) {
  const [q, setQ] = useState(
    "technical founder, AI infra, enterprise traction, no prior VC backing, top-tier accelerator");
  const [res, setRes] = useState<QueryResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true); setErr(null);
    try { setRes(await api.runQuery(q)); } catch (e) { setErr((e as Error).message); }
    setBusy(false);
  };
  return (
    <div className="block">
      <h3>One compound query, one pass — not five manual filters</h3>
      <textarea className="filter" rows={2} value={q} onChange={(e) => setQ(e.target.value)} />
      <button className="minibtn primary" onClick={run} disabled={busy}>
        {busy ? "parsing…" : "Run query"}
      </button>
      {err && <Err msg={err} />}
      {res?.error && <Err msg={res.error} />}
      {res && !res.error && (
        <>
          <div className="chips">
            {res.criteria.map((c, i) => (
              <span key={i} className={`chip ${c.kind === "not_evaluable" ? "chip-na" : ""}`}
                title={c.kind === "not_evaluable" ? c.value : `${c.kind}: ${c.value}`}>
                {c.text}{c.kind === "not_evaluable" ? " ⚠" : ""}
              </span>
            ))}
          </div>
          {res.ignored_criteria.length > 0 && (
            <p className="muted" style={{ fontSize: 12 }}>
              ⚠ not evaluable from Memory (ignored, not guessed):{" "}
              {res.ignored_criteria.map((c) => `"${c.text}" — ${c.reason}`).join("; ")}
            </p>
          )}
          <table className="funnel" style={{ marginTop: 8 }}>
            <thead><tr><th>Founder</th><th>Matched</th><th>Signal / Cov</th></tr></thead>
            <tbody>
              {res.results.map((r) => (
                <tr key={r.id} onClick={() => openFounder(r.id)}>
                  <td className="fname">{r.name}</td>
                  <td>{r.matched_keywords.map((k) => <span key={k} className="src" style={{ marginRight: 3 }}>{k}</span>)}</td>
                  <td><b>{r.signal ?? "—"}</b> · <span className="cov">{Math.round(r.coverage * 100)}%</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
