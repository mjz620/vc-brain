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
          <ThesisList theses={theses} thesis={thesis} setThesis={setThesis}
            refreshTheses={refreshTheses} />
        </div>
        <div>
          <div className="section-h"><h2>Multi-attribute query</h2></div>
          <QueryBox openFounder={openFounder} />
        </div>
      </div>
    </div>
  );
}

/* The list is the interface: which lens is active, and what each one actually says.
   Add / edit / delete are all here rather than an always-open "new" form, which read
   as the only thing you could do. */
function ThesisList({ theses, thesis, setThesis, refreshTheses }: {
  theses: Thesis[]; thesis: string; setThesis: (t: string) => void;
  refreshTheses: () => void;
}) {
  const [editing, setEditing] = useState<Thesis | "new" | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const del = async (t: Thesis) => {
    if (!window.confirm(
      `Delete the "${t.name}" thesis? This removes ${t.file} from disk.`)) return;
    setErr(null);
    try {
      const r = await api.deleteThesis(t.file);
      if (editing !== "new" && editing?.file === t.file) setEditing(null);
      if (t.file === thesis) setThesis(r.next);  // never leave a dead lens selected
      refreshTheses();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  return (
    <>
      <div className="section-h">
        <h2>Theses</h2>
        <span className="count">{theses.length}</span>
        <button className="minibtn th-add" onClick={() => setEditing("new")}>+ New thesis</button>
      </div>
      <p className="th-help">
        Click a thesis to make it the active lens — every page re-runs through it.
        Edit changes it in place; deleting removes its config file.
      </p>
      {err && <Err msg={err} />}
      <div className="th-list">
        {theses.map((t) => {
          const on = t.file === thesis;
          return (
            <div key={t.file} className={`th-row ${on ? "on" : ""}`}>
              <button className="th-pick" onClick={() => setThesis(t.file)} aria-pressed={on}>
                <span className="th-name">{t.name}{on && <span className="th-active">active lens</span>}</span>
                <span className="th-meta">
                  {t.stage} · {t.sectors.join(", ")} · ${t.check_size_usd.toLocaleString()} ·{" "}
                  {t.ownership_target_pct}% target · {t.risk_appetite} risk
                </span>
              </button>
              <span className="th-acts">
                <button className="minibtn" onClick={() => setEditing(t)}
                  aria-label={`edit ${t.name}`}>Edit</button>
                <button className="minibtn th-del" onClick={() => del(t)}
                  aria-label={`delete ${t.name}`}>Delete</button>
              </span>
            </div>
          );
        })}
      </div>
      {editing && (
        <ThesisEditor
          key={editing === "new" ? "new" : editing.file}
          init={editing === "new" ? null : editing}
          onCancel={() => setEditing(null)}
          onSaved={(file) => { setEditing(null); refreshTheses(); setThesis(file); }} />
      )}
    </>
  );
}

const BLANK = {
  name: "", sectors: "", stage: "pre-seed", geography: "",
  check_size_usd: 100000, ownership_target_pct: 8,
  risk_appetite: "high", topics: "",
};

function ThesisEditor({ init, onCancel, onSaved }: {
  init: Thesis | null; onCancel: () => void; onSaved: (file: string) => void;
}) {
  const [cfg, setCfg] = useState(init ? {
    name: init.name, sectors: init.sectors.join(", "), stage: init.stage,
    geography: init.geography.join(", "), check_size_usd: init.check_size_usd,
    ownership_target_pct: init.ownership_target_pct,
    risk_appetite: init.risk_appetite, topics: init.topics.join(", "),
  } : BLANK);
  const [state, setState] = useState<string | null>(null);
  const set = (k: string, v: string | number) => setCfg({ ...cfg, [k]: v });
  const save = async () => {
    if (!cfg.name.trim()) { setState("⚠ a thesis needs a name"); return; }
    setState("saving…");
    try {
      const list = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
      const t = await api.saveThesis({
        ...cfg, name: cfg.name.trim(),
        sectors: list(cfg.sectors), geography: list(cfg.geography),
        topics: list(cfg.topics),
        check_size_usd: Number(cfg.check_size_usd),
        ownership_target_pct: Number(cfg.ownership_target_pct),
        replaces: init?.file ?? null,
      });
      onSaved(t.file);
    } catch (e) {
      setState(`⚠ ${(e as Error).message}`);
    }
  };
  const renamed = init && cfg.name.trim() && cfg.name.trim() !== init.name;
  return (
    <div className="block th-editor">
      <h3>{init ? `Editing — ${init.name}` : "New thesis"}</h3>
      <div className="t-grid">
        <label>Name<input className="filter" value={cfg.name} onChange={(e) => set("name", e.target.value)} /></label>
        <label>Stage<input className="filter" value={cfg.stage} onChange={(e) => set("stage", e.target.value)} /></label>
        <label>Sectors<input className="filter" value={cfg.sectors} onChange={(e) => set("sectors", e.target.value)} /></label>
        <label>Geography<input className="filter" value={cfg.geography} onChange={(e) => set("geography", e.target.value)} /></label>
        <label>Check size $<input className="filter" type="number" min="0" step="1000"
          value={cfg.check_size_usd} onChange={(e) => set("check_size_usd", e.target.value)} /></label>
        <label>Ownership %<input className="filter" type="number" min="0" max="100" step="0.5"
          value={cfg.ownership_target_pct} onChange={(e) => set("ownership_target_pct", e.target.value)} /></label>
        <label>Risk appetite
          <select className="filter" value={cfg.risk_appetite} onChange={(e) => set("risk_appetite", e.target.value)}>
            <option>high</option><option>medium</option><option>low</option>
          </select>
        </label>
        <label>Scan topics<input className="filter" value={cfg.topics} onChange={(e) => set("topics", e.target.value)} /></label>
      </div>
      <div className="th-foot">
        <button className="minibtn primary" onClick={save}>
          {init ? "Save changes" : "Create thesis"}
        </button>
        <button className="minibtn" onClick={onCancel}>Cancel</button>
        {state && !state.startsWith("⚠") && (
          <span className="muted" style={{ fontSize: 12.5 }} aria-live="polite">{state}</span>
        )}
      </div>
      {renamed && (
        <p className="th-help" aria-live="polite">
          Renaming moves the config file — the old {init!.file} is removed on save.
        </p>
      )}
      {state?.startsWith("⚠") && <Err msg={state.slice(2)} />}
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
      <textarea className="filter" rows={2} value={q} onChange={(e) => setQ(e.target.value)}
        aria-label="Multi-attribute query" />
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
          {res.results.length === 0 && (
            <p className="empty">No founders in Memory match every evaluable criterion —
              loosen the query or scan more sources.</p>
          )}
          {res.results.length > 0 && (
            <div className="tablewrap" style={{ marginTop: 8 }}>
            <table className="funnel">
              <thead><tr><th>Founder</th><th>Matched</th><th>Signal / Cov</th></tr></thead>
              <tbody>
                {res.results.map((r) => (
                  <tr key={r.id}>
                    <td className="fname">
                      <button className="rowlink" onClick={() => openFounder(r.id)}>{r.name}</button>
                    </td>
                    <td>{r.matched_keywords.map((k) => <span key={k} className="src" style={{ marginRight: 3 }}>{k}</span>)}</td>
                    <td><b>{r.signal ?? "—"}</b> · <span className="cov">{Math.round(r.coverage * 100)}%</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
