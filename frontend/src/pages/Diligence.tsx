import { useEffect, useMemo, useState } from "react";
import * as api from "../api";
import type { Brief, Claim, Trace } from "../api";
import { Err, FounderSwitcher, Skeleton, TIER_SHORT, TierChip, TracePanel } from "../components";

/* Page 3 — "Watch it argue with itself."
   Claim ledger (contradicted pinned first) + adjudication transcripts via the trace
   panel + the mechanical validator's report, recomputed in the open. */
const TIER_ORDER: Record<string, number> = {
  contradicted: 0, self_reported: 1, single_source: 2, corroborated: 3,
};
const CITE_ID = /\[([a-z]{2,5}-\d{1,3})\b/g;

export default function Diligence({ thesis, founderId, founders, openFounder }: {
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

  const validator = useMemo(() => {
    if (!brief?.memo_md) return null;
    const valid = new Set(brief.claims.map((c) => c.id));
    const cited = [...brief.memo_md.matchAll(CITE_ID)].map((m) => m[1]);
    const unknown = [...new Set(cited.filter((id) => !valid.has(id) && !id.startsWith("open")))];
    return { cited: new Set(cited).size, total: cited.length, unknown };
  }, [brief]);

  if (!founderId) {
    return (
      <div>
        <PageHead founderId={founderId} founders={founders} openFounder={openFounder} />
        {founders.length === 0 && (
          <p className="empty">No diligence runs yet — screen a founder or submit an
            application and the claim ledger appears here.</p>
        )}
        {founders.length > 0 && <p className="muted">Pick a founder with a diligence run:</p>}
        <div className="picker">
          {founders.map((f) => (
            <button key={f.id} className="minibtn" onClick={() => openFounder(f.id)}>{f.name}</button>
          ))}
        </div>
      </div>
    );
  }

  const claims = brief ? [...brief.claims].sort((a, b) =>
    (TIER_ORDER[a.corroboration] ?? 9) - (TIER_ORDER[b.corroboration] ?? 9)
    || b.trust - a.trust) : [];
  const contradicted = claims.filter((c) => c.corroboration === "contradicted");

  return (
    <div>
      <PageHead founderId={founderId} founders={founders} openFounder={openFounder} />
      {err && <Err msg={err} />}
      {!brief && !err && <Skeleton lines={10} />}
      {brief && (
        <div className="memo-wrap">
          <div style={{ flex: 1, minWidth: 0 }}>
            {validator && (
              <div className="block" style={{ marginBottom: 14 }}>
                <h3>Mechanical validator — no LLM in this check</h3>
                <div className="v-row">
                  <span className={`v-stat ${validator.unknown.length ? "bad" : "good"}`}>
                    {validator.unknown.length === 0
                      ? `✓ all ${validator.cited} cited claim ids exist in the ledger`
                      : `✗ ${validator.unknown.length} fabricated citation(s): ${validator.unknown.join(", ")}`}
                  </span>
                  <span className="v-stat">{brief.claims.length} claims in ledger</span>
                  <span className="v-stat">{contradicted.length} contradicted</span>
                </div>
              </div>
            )}

            {contradicted.length > 0 && (
              <div className="spotlight">
                <div className="spot-head">
                  <h2>⚠ Contradiction spotlight</h2>
                  <span className="spot-count">
                    {contradicted.length} of {brief.claims.length} claims contradicted —
                    read these before anything else
                  </span>
                </div>
                {contradicted.map((c) => (
                  <div key={c.id}>
                    <ClaimRow c={c} active={traceId === c.id}
                      onClick={() => setTraceId(c.id)} />
                    {traceId === c.id && founderId && (
                      <VerdictLine founderId={founderId} claimId={c.id} />
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="section-h"><h2>Claim ledger — grouped by tier</h2>
              <span className="count">click any claim for its full trace</span></div>
            {claims.length === 0 && <p className="empty">no claims extracted for this founder.</p>}
            {(() => {
              const rest = claims.filter((c) => c.corroboration !== "contradicted");
              let lastTier: string | null = null;
              return rest.map((c) => {
                const showHeader = c.corroboration !== lastTier;
                lastTier = c.corroboration;
                return (
                  <div key={c.id}>
                    {showHeader && (
                      <h4 className="tier-h">{TIER_SHORT[c.corroboration] || c.corroboration}</h4>
                    )}
                    <ClaimRow c={c} active={traceId === c.id} onClick={() => setTraceId(c.id)} />
                  </div>
                );
              });
            })()}
          </div>
          {traceId && (
            <TracePanel founderId={founderId} claimId={traceId}
              onClose={() => setTraceId(null)} />
          )}
        </div>
      )}
    </div>
  );
}

function PageHead({ founderId, founders, openFounder }: {
  founderId: string | null;
  founders: { id: string; name: string }[]; openFounder: (id: string) => void;
}) {
  const name = founderId ? founderId.replace("founder-", "") : null;
  return (
    <div className="page-h">
      <h1>Diligence{name ? <span className="h-founder"> · {name}</span> : ""}</h1>
      <FounderSwitcher founderId={founderId} founders={founders} openFounder={openFounder} />
      <p className="page-sub">
        Workers extract claims; contested claims go through a <b>prosecutor → defender
        → judge</b> debate whose verdict overrides the rubric; a no-LLM validator
        rejects any citation to a claim that doesn't exist.
      </p>
    </div>
  );
}

/* Adjudication verdict one-liner, fetched only when the claim is clicked
   (shared trace cache — the panel and this line cost one request total). */
function VerdictLine({ founderId, claimId }: { founderId: string; claimId: string }) {
  const [trace, setTrace] = useState<Trace | null>(null);
  useEffect(() => {
    let live = true;
    setTrace(null);
    api.getTraceCached(founderId, claimId).then((t) => { if (live) setTrace(t); }).catch(() => {});
    return () => { live = false; };
  }, [founderId, claimId]);
  if (!trace) return <div className="claim-verdict">…</div>;
  if (!trace.adjudication) return <div className="claim-verdict">uncontested — rubric-anchored, no debate needed</div>;
  return (
    <div className="claim-verdict">
      judge: trust <b>{trace.rubric_trust.toFixed(2)} → {trace.adjudication.trust.toFixed(2)}</b>
      {" — "}{trace.adjudication.rationale}
    </div>
  );
}

function ClaimRow({ c, active, onClick }: { c: Claim; active: boolean; onClick: () => void }) {
  return (
    <button className={`claimrow ${active ? "active" : ""}`} onClick={onClick}
      aria-label={`${c.id}, ${c.corroboration} — open full trace`}>
      <span className="cr-id">{c.id}</span>
      <TierChip tier={c.corroboration} trust={c.trust} />
      <span className="cr-axis">{c.axis}</span>
      <span className="cr-text">{c.text}</span>
    </button>
  );
}
