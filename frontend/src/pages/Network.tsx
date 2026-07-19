import { useEffect, useMemo, useState } from "react";
import * as api from "../api";
import type { Network } from "../api";
import { Err, Skeleton } from "../components";

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
          <Graph n={n} />
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

type Hover = { kind: "channel" | "startup" | "investor"; key: string } | null;

function Graph({ n }: { n: Network }) {
  const [hover, setHover] = useState<Hover>(null);

  const layout = useMemo(() => {
    const channels = Object.keys(n.channels);
    const investors = Array.from(new Set(n.startups.flatMap((s) => s.investors)));
    const startups = n.startups;
    const rows = Math.max(channels.length, startups.length, investors.length);
    const H = 40 + (rows - 1) * 26;
    const col = (items: string[], x: number) => {
      const m = new Map<string, { x: number; y: number }>();
      const pad = 20;
      items.forEach((it, i) => {
        const y = items.length === 1 ? H / 2
          : pad + i * (H - 2 * pad) / (items.length - 1);
        m.set(it, { x, y });
      });
      return m;
    };
    return {
      H,
      channels, investors, startups,
      cpos: col(channels, 74),
      spos: col(startups.map((s) => s.name), 360),
      ipos: col(investors, 646),
    };
  }, [n]);

  const { H, channels, investors, startups, cpos, spos, ipos } = layout;
  const W = 760;

  // Which nodes are active given the hovered node.
  const active = useMemo(() => {
    const s = new Set<string>(), c = new Set<string>(), i = new Set<string>();
    if (!hover) return { s, c, i };
    if (hover.kind === "channel") {
      c.add(hover.key);
      startups.filter((x) => x.channel === hover.key).forEach((x) => {
        s.add(x.name); x.investors.forEach((v) => i.add(v));
      });
    } else if (hover.kind === "startup") {
      const st = startups.find((x) => x.name === hover.key);
      if (st) { s.add(st.name); c.add(st.channel); st.investors.forEach((v) => i.add(v)); }
    } else {
      i.add(hover.key);
      startups.filter((x) => x.investors.includes(hover.key)).forEach((x) => {
        s.add(x.name); c.add(x.channel);
      });
    }
    return { s, c, i };
  }, [hover, startups]);

  const dim = (on: boolean) => (hover && !on ? " dim" : "");
  const bez = (x1: number, y1: number, x2: number, y2: number) => {
    const mx = (x1 + x2) / 2;
    return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
  };

  return (
    <div className="net-graph">
      <svg viewBox={`0 0 ${W} ${H}`} role="img"
        aria-label="sourcing network: channels to startups to seed investors — full data in the tables below">
        {/* channel -> startup edges */}
        {startups.map((s) => {
          const a = cpos.get(s.channel)!, b = spos.get(s.name)!;
          const on = active.s.has(s.name);
          return <path key={`c-${s.name}`} className={`edge${hover && on ? " hot" : ""}${dim(on)}`}
            d={bez(a.x + 56, a.y, b.x - 62, b.y)} />;
        })}
        {/* startup -> investor edges */}
        {startups.flatMap((s) => s.investors.map((inv) => {
          const a = spos.get(s.name)!, b = ipos.get(inv)!;
          const on = active.s.has(s.name) && active.i.has(inv);
          return <path key={`i-${s.name}-${inv}`} className={`edge${hover && on ? " hot" : ""}${dim(on)}`}
            d={bez(a.x + 62, a.y, b.x - 4, b.y)} />;
        }))}
        {/* channel nodes */}
        {channels.map((ch) => {
          const p = cpos.get(ch)!;
          return (
            <g key={ch} className={`nnode nnode-ch${dim(active.c.has(ch))}`}
              onMouseEnter={() => setHover({ kind: "channel", key: ch })}
              onMouseLeave={() => setHover(null)}>
              <title>{ch}</title>
              <rect x={p.x - 56} y={p.y - 11} width={112} height={22} rx={6} />
              <text x={p.x} y={p.y + 4} textAnchor="middle">{trunc(ch, 16)}</text>
            </g>
          );
        })}
        {/* startup nodes */}
        {startups.map((s) => {
          const p = spos.get(s.name)!;
          return (
            <g key={s.name} className={`nnode nnode-st${dim(active.s.has(s.name))}`}
              onMouseEnter={() => setHover({ kind: "startup", key: s.name })}
              onMouseLeave={() => setHover(null)}>
              <title>{`${s.name} — ${s.channel} ${s.batch} · ${s.outcome} · seed: ${s.investors.join(", ")}`}</title>
              <rect x={p.x - 62} y={p.y - 10} width={124} height={20} rx={5} />
              <text x={p.x} y={p.y + 4} textAnchor="middle">{s.name}</text>
            </g>
          );
        })}
        {/* investor nodes */}
        {investors.map((inv) => {
          const p = ipos.get(inv)!;
          return (
            <g key={inv} className={`nnode nnode-inv${dim(active.i.has(inv))}`}
              onMouseEnter={() => setHover({ kind: "investor", key: inv })}
              onMouseLeave={() => setHover(null)}>
              <title>{inv}</title>
              <rect x={p.x - 4} y={p.y - 10} width={110} height={20} rx={5} />
              <text x={p.x + 4} y={p.y + 4}>{trunc(inv, 16)}</text>
            </g>
          );
        })}
      </svg>
      <div className="net-legend">
        <span className="net-lg net-lg-ch">sourcing channel</span>
        <span className="net-lg net-lg-st">startup</span>
        <span className="net-lg net-lg-inv">seed investor</span>
        <span className="muted">hover any node to trace its connections</span>
      </div>
    </div>
  );
}

function trunc(s: string, n: number) { return s.length > n ? s.slice(0, n - 1) + "…" : s; }
