import { useEffect, useMemo, useState } from "react";
import * as api from "../api";
import type { Brief, Claim } from "../api";
import { Err, Skeleton, TierChip, TracePanel } from "../components";

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
        <PageHead />
        <p className="muted">Pick a founder with a diligence run:</p>
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
      <PageHead name={founderId.replace("founder-", "")} />
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
              <>
                <div className="section-h"><h2>⚠ Contradicted — read first</h2></div>
                {contradicted.map((c) => (
                  <ClaimRow key={c.id} c={c} active={traceId === c.id}
                    onClick={() => setTraceId(c.id)} />
                ))}
              </>
            )}

            <div className="section-h"><h2>Claim ledger — grouped by tier</h2>
              <span className="count">click any claim for its full trace</span></div>
            {claims.filter((c) => c.corroboration !== "contradicted").map((c) => (
              <ClaimRow key={c.id} c={c} active={traceId === c.id}
                onClick={() => setTraceId(c.id)} />
            ))}
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

function PageHead({ name }: { name?: string }) {
  return (
    <div className="page-h">
      <h1>Diligence{name ? <span className="h-founder"> · {name}</span> : ""}</h1>
      <p className="page-sub">
        Workers extract claims; contested claims go through a <b>prosecutor → defender
        → judge</b> debate whose verdict overrides the rubric; a no-LLM validator
        rejects any citation to a claim that doesn't exist.
      </p>
    </div>
  );
}

function ClaimRow({ c, active, onClick }: { c: Claim; active: boolean; onClick: () => void }) {
  return (
    <div className={`claimrow ${active ? "active" : ""}`} onClick={onClick}>
      <span className="cr-id">{c.id}</span>
      <TierChip tier={c.corroboration} trust={c.trust} />
      <span className="cr-axis">{c.axis}</span>
      <span className="cr-text">{c.text}</span>
    </div>
  );
}
