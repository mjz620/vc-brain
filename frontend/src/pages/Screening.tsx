import { useEffect, useState } from "react";
import * as api from "../api";
import type { FounderRow } from "../api";
import { AXES, AXLABEL, Err, InfoTip, Meters, Skeleton, Sparkline, stanceClass, TrendGlyph } from "../components";

/* Page 2 — "Three independent verdicts, never averaged." */
export default function Screening({ thesis, openFounder }:
  { thesis: string; openFounder: (id: string) => void }) {
  const [founders, setFounders] = useState<FounderRow[] | null>(null);
  const [killed, setKilled] = useState<{ id: string; reason: string }[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    setFounders(null);
    api.getFounders(thesis).then(setFounders).catch((e) => setErr(e.message));
    api.getKilled().then(setKilled).catch(() => {});
  }, [thesis]);

  const isApp = (f: FounderRow) => f.has_memo || f.source === "deck";
  const apps = (founders || []).filter(isApp);
  const rest = (founders || []).filter((f) => !isApp(f)).filter((f) =>
    (f.name + f.source).toLowerCase().includes(filter.toLowerCase()));

  return (
    <div>
      <div className="page-h">
        <h1>Screening</h1>
        <p className="page-sub">
          Every opportunity scored on <b>three independent axes — never averaged</b>.
          The Founder Score chip is a persistent, cross-application <em>input</em> to
          the Founder axis, not a substitute for it. Trends come from append-only score history.
        </p>
      </div>
      {err && <Err msg={err} />}
      {!founders && !err && <Skeleton lines={8} />}

      {apps.length > 0 && (
        <>
          <div className="section-h"><h2>Applications in diligence</h2>
            <span className="count">{apps.length}</span></div>
          <div className="apps">
            {apps.map((f) => <FounderCard key={f.id} f={f} onOpen={() => openFounder(f.id)} />)}
          </div>
        </>
      )}

      {founders && (
        <>
          <div className="section-h"><h2>Screened funnel — this thesis lens</h2>
            <span className="count">{rest.length}</span></div>
          <input className="filter" placeholder="filter by name / source…"
            value={filter} onChange={(e) => setFilter(e.target.value)} />
          {rest.length === 0 ? (
            <p className="empty">
              {filter ? "no founders match this filter." : "no founders screened under this thesis yet."}
            </p>
          ) : (
          <div className="tablewrap">
          <table className="funnel">
            <thead>
              <tr><th>Founder</th><th>Source</th><th>Signal / Coverage</th>
                <th>Founder <InfoTip kind="axis" axis="founder" /></th>
                <th>Market <InfoTip kind="axis" axis="market" /></th>
                <th>Idea vs Mkt <InfoTip kind="axis" axis="idea" /></th></tr>
            </thead>
            <tbody>
              {rest.map((f) => {
                const ax = Object.fromEntries(f.axes.map((a) => [a.axis, a]));
                const unscreened = f.axes.every((a) => a.score == null);
                return (
                  <tr key={f.id}>
                    <td className="fname">
                      <button className="rowlink" onClick={() => openFounder(f.id)}>{f.name}</button>
                    </td>
                    <td><span className="src">{f.source}</span></td>
                    <td title={`persistent Founder Score · ${f.score_history_points} history points`}>
                      <Meters signal={f.signal} coverage={f.coverage} founderId={f.id} />
                    </td>
                    {unscreened
                      ? <td colSpan={3} className="muted">not screened under this thesis</td>
                      : AXES.map((k) => {
                        const a = ax[k];
                        return (
                          <td key={k} className={`axmini ${stanceClass(a?.stance)}`}>
                            {a && a.score != null
                              ? <>{a.score} <TrendGlyph trend={a.trend} /><em>{a.stance}</em></> : "—"}
                          </td>
                        );
                      })}
                  </tr>
                );
              })}
            </tbody>
          </table>
          </div>
          )}
        </>
      )}

      {killed.length > 0 && (
        <div className="killed">
          <div className="section-h"><h2>First-pass kill screen</h2>
            <span className="count">{killed.length} removed before diligence — reason logged</span></div>
          {killed.map((k) => (
            <div key={k.id} className="kill"><b>{k.id.replace("founder-", "")}</b> — {k.reason}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function FounderCard({ f, onOpen }: { f: FounderRow; onOpen: () => void }) {
  const ax = Object.fromEntries(f.axes.map((a) => [a.axis, a]));
  return (
    <div className="card">
      <div className="top">
        <button className="rowlink name" onClick={onOpen}>{f.name}</button>
        <span className="pill">{f.source === "deck" ? "inbound" : f.source}</span>
        {f.score_history?.length > 0 && (
          <span className="sc" title="Founder Score history — hover a point for its trigger">
            <Sparkline history={f.score_history} />
          </span>
        )}
      </div>
      <div className="axrow">
        {AXES.map((k) => {
          const a = ax[k];
          return (
            <div key={k} className={`axcell ${stanceClass(a?.stance)}`}>
              <div className="k">{AXLABEL[k]} <InfoTip kind="axis" axis={k} /></div>
              <div className="v">
                {a && a.score != null
                  ? <>{a.score}<small><TrendGlyph trend={a.trend} /> {a.stance}</small></> : "—"}
              </div>
            </div>
          );
        })}
      </div>
      <Meters signal={f.signal} coverage={f.coverage} founderId={f.id} />
    </div>
  );
}
