import { useEffect, useState } from "react";
import * as api from "../api";
import type { AskResult, Axis, Brief } from "../api";
import {
  AXES, AXLABEL, Err, FounderSwitcher, inline, Memo, ProvenanceGraph, Skeleton,
  Sparkline, stanceClass, TracePanel, TREND,
} from "../components";

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
        <div className="page-h">
          <h1>Memo &amp; Decision</h1>
          <FounderSwitcher founderId={founderId} founders={founders} openFounder={openFounder} />
        </div>
        {founders.length === 0
          ? <p className="empty">No memos yet — run a founder through diligence
              (or submit an application on the Sourcing page) and the decision lands here.</p>
          : <>
              <p className="muted">Pick a founder:</p>
              <div className="picker">
                {founders.map((f) => (
                  <button key={f.id} className="minibtn" onClick={() => openFounder(f.id)}>{f.name}</button>
                ))}
              </div>
            </>}
      </div>
    );
  }

  const rec = brief?.recommendation || {};
  const d = brief?.decision || "none";
  const axById = Object.fromEntries((brief?.axes || []).map((a) => [a.axis, a]));
  // Axis → the trace of its highest-trust claim (cheap: claims ship with the brief).
  const topClaim = (axis: string) => {
    const c = (brief?.claims || []).filter((c) => c.axis === axis)
      .sort((a, b) => b.trust - a.trust)[0];
    return c?.id ?? null;
  };

  return (
    <div>
      <div className="page-h">
        <h1>Memo &amp; Decision<span className="h-founder"> · {founderId.replace("founder-", "")}</span></h1>
        <FounderSwitcher founderId={founderId} founders={founders} openFounder={openFounder} />
        {brief?.memo_md && (
          <a className="minibtn" href={`/api/memo/${founderId}.pdf?thesis=${encodeURIComponent(thesis)}`}
            target="_blank" rel="noreferrer" title="download a shareable investment-memo PDF">
            ↓ PDF
          </a>
        )}
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
              {brief.score_history?.length > 0 && (
                <span className="hist" title="persistent Founder Score history — append-only">
                  <span className="m-k">F-Score</span>
                  <Sparkline history={brief.score_history} />
                </span>
              )}
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
                  const tc = topClaim(k);
                  const inner = (
                    <>
                      <span className="lbl">{AXLABEL[k]}</span>
                      <span className="bar"><span className={stanceClass(a?.stance)} style={{ width: `${sc * 10}%` }} /></span>
                      <span className="num">
                        {a && a.score != null ? <>{a.score} {TREND[a.trend || "new"]} <em>{a.stance}</em></> : "—"}
                      </span>
                    </>
                  );
                  // A clickable axis is a real button (keyboard-operable); a non-clickable
                  // one stays a plain row.
                  return tc ? (
                    <button className="axline" key={k} onClick={() => setTraceId(tc)}
                      aria-label={`${AXLABEL[k]} axis — open the trace of its top claim ${tc}`}>
                      {inner}
                    </button>
                  ) : (
                    <div className="axline" key={k}>{inner}</div>
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

          <div className="block" style={{ marginBottom: 16 }}>
            <h3>Latency — first signal → decision</h3>
            <div className="strip">
              {brief.latency.stages.map(([s, sec]) => (
                <span key={s} className="lat">{s} <b>{sec.toFixed(2)}s</b></span>
              ))}
              <span className="lat total">total <b>{brief.latency.total_seconds.toFixed(2)}s</b></span>
            </div>
          </div>

          {rec.claims_it_turns_on?.length ? (
            <details className="provwrap" open>
              <summary>Provenance — what the decision rests on</summary>
              <ProvenanceGraph decision={d} turnsOn={rec.claims_it_turns_on}
                claims={brief.claims} totalClaims={brief.claims.length}
                onOpenClaim={setTraceId} />
            </details>
          ) : null}

          <div className="memo-wrap">
            <div style={{ flex: 1, minWidth: 0 }}>
              {brief.memo_md ? (
                <>
                  <Memo md={brief.memo_md} onCite={setTraceId} />
                  <AskMemo founderId={brief.founder_id} onCite={setTraceId} />
                </>
              ) : (
                <p className="empty">No memo yet — this founder was sourced and screened but not
                  put through full diligence.</p>
              )}
            </div>
            {traceId && (
              <TracePanel founderId={brief.founder_id} claimId={traceId}
                onClose={() => setTraceId(null)} />
            )}
          </div>
        </>
      )}
    </div>
  );
}

/* "Ask this memo": grounded Q&A over the claim ledger. Citations are the same
   clickable chips as the memo; a refusal is an honest gap, not an error. */
function AskMemo({ founderId, onCite }: { founderId: string; onCite: (id: string) => void }) {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<AskResult | null>(null);
  const [askErr, setAskErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const ask = async () => {
    if (!q.trim()) return;
    setBusy(true); setAskErr(null); setRes(null);
    try {
      setRes(await api.postAsk(founderId, q));
    } catch (e) {
      setAskErr((e as Error).message); // 429 rate-limit detail surfaces verbatim
    }
    setBusy(false);
  };

  return (
    <div className="ask">
      <div className="section-h" style={{ margin: "0 0 8px" }}>
        <h2>Ask this memo</h2>
        <span className="count">answers only from the claim ledger — cited, validated, or refused</span>
      </div>
      <div className="ask-row">
        <input className="filter" placeholder="e.g. What is the strongest evidence of traction?"
          value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !busy && ask()} />
        <button className={`minibtn primary${busy ? " pulse" : ""}`} onClick={ask}
          disabled={busy || !q.trim()}>
          {busy ? "asking…" : "Ask"}
        </button>
      </div>
      {askErr && <Err msg={askErr} />}
      {res && (
        res.refused ? (
          <div className="ask-refused">
            <span className="gap-badge">gap</span>
            <b>Refused — the ledger can't support an answer.</b> {res.answer}
          </div>
        ) : (
          <>
            <p className="ask-a">{inline(res.answer, onCite)}</p>
            {res.validated ? (
              <div className="ask-valid">
                ✓ validated — every citation ({res.cited_claim_ids.join(", ") || "none"}) exists in the ledger
              </div>
            ) : (
              <div className="ask-valid bad">
                ✗ validator stripped {res.invalid_citations.length} citation(s) that don't exist
                in the ledger: {res.invalid_citations.join(", ")}
              </div>
            )}
          </>
        )
      )}
    </div>
  );
}
