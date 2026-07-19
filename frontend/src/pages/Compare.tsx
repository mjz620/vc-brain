import { useEffect, useState } from "react";
import * as api from "../api";
import type { Brief, FounderRow } from "../api";
import { AXES, AXLABEL, Err, Meters, Skeleton, Sparkline, stanceClass, TrendGlyph } from "../components";

/* Page 6 — side-by-side comparison. Columns are founders; rows are the three
   independent axes (score + stance + trend — NEVER averaged or totaled),
   the Signal/Coverage split, decision, and latency. */
const MAX = 3;

export default function Compare({ thesis, openFounder }:
  { thesis: string; openFounder: (id: string) => void }) {
  const [rows, setRows] = useState<FounderRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sel, setSel] = useState<string[]>([]);
  const [briefs, setBriefs] = useState<Record<string, Brief>>({});

  useEffect(() => {
    setRows(null); setSel([]); setBriefs({});
    api.getFounders(thesis).then(setRows).catch((e) => setErr(e.message));
  }, [thesis]);

  // Decision comes from the existing per-founder brief — fetched lazily for the
  // 2–3 selected founders only, never for the whole list.
  useEffect(() => {
    for (const id of sel) {
      const row = rows?.find((r) => r.id === id);
      if (!row?.has_memo || briefs[id]) continue;
      api.getFounder(id, thesis).then((b) =>
        setBriefs((prev) => (prev[id] ? prev : { ...prev, [id]: b }))).catch(() => {});
    }
  }, [sel, rows, briefs, thesis]);

  // At MAX, adding a new pick is a no-op rather than silently evicting the oldest —
  // the picker button below is disabled instead, so nothing changes without an
  // explicit deselect first.
  const toggle = (id: string) => setSel((s) =>
    s.includes(id) ? s.filter((x) => x !== id)
      : s.length >= MAX ? s : [...s, id]);

  const screened = (rows || []).filter((f) => f.axes.some((a) => a.score != null));
  const picked = sel.map((id) => screened.find((f) => f.id === id))
    .filter((f): f is FounderRow => !!f);

  return (
    <div>
      <div className="page-h">
        <h1>Compare</h1>
        <p className="page-sub">
          Two or three opportunities side by side. The three axes stay separate —
          <b> there is no combined score to sort by</b>; the comparison is the analysis.
        </p>
      </div>
      {err && <Err msg={err} />}
      {!rows && !err && <Skeleton lines={6} />}
      {rows && (
        <>
          <div className="section-h"><h2>Pick 2–3 from the screened funnel</h2>
            <span className="count">{sel.length}/{MAX} selected</span></div>
          <div className="cmp-pick">
            {screened.map((f) => (
              <button key={f.id}
                className={`minibtn ${sel.includes(f.id) ? "primary" : ""}`}
                disabled={!sel.includes(f.id) && sel.length >= MAX}
                title={!sel.includes(f.id) && sel.length >= MAX
                  ? `deselect one first — comparing max ${MAX} at a time` : undefined}
                onClick={() => toggle(f.id)}>{f.name}</button>
            ))}
          </div>

          {picked.length < 2 ? (
            <p className="empty">Select at least two founders above to compare them
              axis by axis.</p>
          ) : (
            <div className="tablewrap">
              <table className="funnel cmp">
                <thead>
                  <tr>
                    <th />
                    {picked.map((f) => (
                      <th key={f.id} className="colh">
                        <button className="rowlink" onClick={() => openFounder(f.id)}
                          title="open memo & decision">{f.name}</button>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {AXES.map((k) => (
                    <tr key={k}>
                      <td className="rowh">{AXLABEL[k]}</td>
                      {picked.map((f) => {
                        const a = f.axes.find((x) => x.axis === k);
                        return (
                          <td key={f.id}>
                            {a && a.score != null ? (
                              <>
                                <span className={`cmp-score ${stanceClass(a.stance)}`}>
                                  {a.score} <TrendGlyph trend={a.trend} />
                                </span>
                                <span className={`axmini ${stanceClass(a.stance)}`}>
                                  <em>{a.stance}</em>
                                </span>
                              </>
                            ) : <span className="cmp-note">not screened under this thesis</span>}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                  <tr className="cmp-sep">
                    <td className="rowh">Signal / Coverage</td>
                    {picked.map((f) => (
                      <td key={f.id}><Meters signal={f.signal} coverage={f.coverage} /></td>
                    ))}
                  </tr>
                  <tr>
                    <td className="rowh">Score history</td>
                    {picked.map((f) => (
                      <td key={f.id}>
                        {f.score_history?.length
                          ? <Sparkline history={f.score_history} />
                          : <span className="cmp-note">no history</span>}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="rowh">Decision</td>
                    {picked.map((f) => {
                      const b = briefs[f.id];
                      return (
                        <td key={f.id}>
                          {!f.has_memo
                            ? <span className="cmp-note">no memo — not through diligence</span>
                            : b
                              ? <span className={`badge ${b.decision || "none"}`}>{b.decision || "none"}</span>
                              : <span className="cmp-note">loading…</span>}
                        </td>
                      );
                    })}
                  </tr>
                  <tr>
                    <td className="rowh">Latency</td>
                    {picked.map((f) => (
                      <td key={f.id} className="axmini">
                        {f.latency_total ? `${f.latency_total.toFixed(2)}s` : "—"}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
