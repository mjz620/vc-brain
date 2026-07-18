import { useEffect, useState } from "react";
import * as api from "../api";
import type { Axis, Brief } from "../api";
import { AXES, AXLABEL, Err, Memo, Skeleton, stanceClass, TracePanel, TREND } from "../components";

/* Page 4 — "A decision you could act on in 24h, every sentence traceable." */
export default function Decision({ thesis, founderId, founders, openFounder }: {
  thesis: string; founderId: string | null;
  founders: { id: string; name: string }[]; openFounder: (id: string) => void;
}) {
  const [brief, setBrief] = useState<Brief | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [traceId, setTraceId] = useState<string | null>(null);

  useEffect(() => {
    setBrief(null); setErr(null); setTraceId(null);
    if (founderId) {
      api.getFounder(founderId, thesis).then(setBrief).catch((e) => setErr(e.message));
    }
  }, [founderId, thesis]);

  if (!founderId) {
    return (
      <div>
        <div className="page-h"><h1>Memo &amp; Decision</h1></div>
        <p className="muted">Pick a founder:</p>
        <div className="picker">
          {founders.map((f) => (
            <button key={f.id} className="minibtn" onClick={() => openFounder(f.id)}>{f.name}</button>
          ))}
        </div>
      </div>
    );
  }

  const rec = brief?.recommendation || {};
  const d = brief?.decision || "none";
  const axById = Object.fromEntries((brief?.axes || []).map((a) => [a.axis, a]));

  return (
    <div>
      <div className="page-h">
        <h1>Memo &amp; Decision<span className="h-founder"> · {founderId.replace("founder-", "")}</span></h1>
        <p className="page-sub">Recommendation first; every factual sentence carries its claim id —
          click one to trace it to the raw signal. Gaps are flagged in the brief's own words, never filled.</p>
      </div>
      {err && <Err msg={err} />}
      {!brief && !err && <Skeleton lines={10} />}
      {brief && (
        <>
          <div className="rec-card">
            <div className="head">
              <span className={`badge ${d}`}>{d}</span>
              <h1>{brief.founder_id.replace("founder-", "")}</h1>
              {rec.amount_usd ? <span className="amt"><b>${rec.amount_usd.toLocaleString()}</b> check</span> : null}
            </div>
            {rec.claims_it_turns_on?.length ? (
              <div className="turns">turns on
                {rec.claims_it_turns_on.map((id) => (
                  <button key={id} className="cite" onClick={() => setTraceId(id)}>[{id}]</button>
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
                    {g.status === "gap" ? <><span className="gap-badge">gap</span> {g.rendered}</>
                      : `${g.field}: disclosed`}
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
              <Memo md={brief.memo_md} onCite={setTraceId} />
              {traceId && (
                <TracePanel founderId={brief.founder_id} claimId={traceId}
                  onClose={() => setTraceId(null)} />
              )}
            </div>
          ) : (
            <p className="muted">No memo yet — this founder was sourced and screened but not
              put through full diligence.</p>
          )}
        </>
      )}
    </div>
  );
}
