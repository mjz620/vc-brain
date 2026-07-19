import { useEffect, useState } from "react";
import * as api from "../api";
import type { Network } from "../api";
import { Err, Skeleton } from "../components";
import ForceGraph from "../components/ForceGraph";

/* Page — Sourcing & Network Intelligence (brief Stretch Goal 3).
   A knowledge graph of how notable startups became visible (sourcing channel) and
   who backed them early (seed investors), joined with this instance's LIVE channel
   yield. The graph is a hover-to-explore enhancement; every fact it shows also
   lives in the accessible tables below it. */
export default function NetworkPage() {
  const [n, setN] = useState<Network | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { api.getNetwork().then(setN).catch((e) => setErr(e.message)); }, []);

  return (
    <div>
      <div className="page-h">
        <h1>Sourcing Network</h1>
        <p className="page-sub">
          The graph through which founders become visible — sourcing channels →
          startups → the investors who backed them early — mapped over known public
          outcomes and joined with this pipeline's own live channel yield. It answers
          the sourcing question the brief calls least-solved: <b>which channels
          historically produce quality</b>, and which ones we're not scanning yet.
        </p>
      </div>
      {err && <Err msg={err} />}
      {!n && !err && <Skeleton lines={10} />}
      {n && (
        <>
          <GraphPanel n={n} />
          <div className="net-cols">
            <div>
              <div className="section-h"><h2>Channel yield — history × live</h2></div>
              <div className="tablewrap">
                <table className="funnel">
                  <thead>
                    <tr><th>Sourcing channel</th><th>Notable outcomes</th>
                      <th>This pipeline (live)</th></tr>
                  </thead>
                  <tbody>
                    {n.channel_intelligence.map((c) => (
                      <tr key={c.channel}>
                        <td className="fname">{c.channel}
                          <div className="net-ch-desc">{c.description}</div>
                        </td>
                        <td>
                          <b className="net-num">{c.historical_successes}</b>
                          <div className="net-notable">{c.notable.join(", ") || "—"}</div>
                        </td>
                        <td>
                          {c.live ? (
                            <span className="net-live">
                              <b className="net-num">{Math.round(c.live.resolve_rate * 100)}%</b> resolve
                              · {c.live.founders} founders
                            </span>
                          ) : (
                            <span className="net-gap">no live scanner ⚠</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {n.underexplored_channels.length > 0 && (
                <div className="suggestion" style={{ marginTop: 10 }}>
                  💡 Underexplored: {n.underexplored_channels.join(", ")} produced notable
                  outcomes but this scanner has no channel for {n.underexplored_channels.length > 1 ? "them" : "it"} —
                  the highest-leverage sourcing edges to add.
                </div>
              )}
            </div>
            <div>
              <div className="section-h"><h2>Network hubs — investors across outcomes</h2></div>
              <ul className="net-hubs">
                {n.top_investors.map((inv) => (
                  <li key={inv.name}>
                    <span className="net-hub-n">{inv.name}</span>
                    <span className="net-hub-c">{inv.count}</span>
                    <span className="net-hub-s">{inv.startups.join(", ")}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <p className="net-note">{n.note}</p>
        </>
      )}
    </div>
  );
}

function GraphPanel({ n }: { n: Network }) {
  const [hovered, setHovered] = useState<string | null>(null);
  return (
    <div className="net-graph">
      <ForceGraph data={n} onHover={setHovered} />
      <div className="net-legend">
        <span className="net-lg net-lg-ch">sourcing channel</span>
        <span className="net-lg net-lg-st">notable outcome</span>
        <span className="net-lg net-lg-inv">seed investor</span>
        <span className="net-lg net-lg-fr">our live pipeline</span>
        <span className="net-cap">
          {hovered ? <b>{hovered}</b> : (
            <>drag a node to throw it · hover to trace connections · node size = influence
              ({n.counts.startups} outcomes · {n.counts.channels} channels ·
              {" "}{n.counts.investors} investors ·
              {" "}<b>{n.counts.live_founders} live founders we're sourcing now</b>)</>
          )}
        </span>
      </div>
    </div>
  );
}
