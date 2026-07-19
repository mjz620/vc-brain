import { useEffect, useRef, useState } from "react";
import type { Network } from "../api";

/* A hand-rolled force-directed graph — no charting library (per DESIGN.md).
   Repulsion + spring + centering physics on an ALPHA-COOLING schedule: the graph
   animates to a settled layout in a few seconds, then FREEZES (crucial — a loop
   that never stops makes every node shimmer at the sub-pixel level, which reads as
   on-screen artifacting). Grabbing a node reheats it, so you can throw it and watch
   the cluster bounce and re-settle. Positions are mutated imperatively each frame
   (refs, not React state) so it holds 60fps; only hover highlight goes through
   React. Honors reduced-motion: settles synchronously, no animation. */

interface SimNode {
  id: string; type: string; label: string; r: number; mass: number;
  x: number; y: number; vx: number; vy: number; fixed: boolean;
}
interface SimLink { s: SimNode; t: SimNode; rest: number; }

const W = 780, H = 560;
const REPULSION = 1400, SPRING = 0.05, CENTER = 0.004, DAMP = 0.82, MAXV = 20;
const ALPHA_DECAY = 0.022, ALPHA_MIN = 0.02;

function radius(type: string, size: number): number {
  if (type === "channel") return 11 + Math.sqrt(size) * 3.4;
  if (type === "investor") return 5 + Math.sqrt(size) * 2.6;
  if (type === "founder") return 3.2 + Math.sqrt(size) * 1.1; // live: signal 0–10 -> r 3.2–6.7
  return 4 + size * 1.6; // startup: tier weight 2–4 -> r 7–10
}

export default function ForceGraph({ data, onHover }: {
  data: Network; onHover?: (label: string | null) => void;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const sim = useRef<{ nodes: SimNode[]; links: SimLink[]; adj: Map<string, Set<string>> } | null>(null);
  const gEls = useRef<Map<string, SVGGElement>>(new Map());
  const lEls = useRef<(SVGLineElement | null)[]>([]);
  const drag = useRef<{ n: SimNode; px: number; py: number } | null>(null);
  const raf = useRef<number>(0);
  const alpha = useRef(1);
  const running = useRef(false);
  const kick = useRef<(a?: number) => void>(() => {});
  const [hover, setHover] = useState<string | null>(null);
  const reduce = typeof matchMedia !== "undefined"
    && matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    const map = new Map<string, SimNode>();
    data.nodes.forEach((n, i) => {
      const ang = (i / data.nodes.length) * Math.PI * 2;
      const rad = 60 + ((i * 53) % 150); // spread out, deterministic-ish
      const r = radius(n.type, n.size);
      map.set(n.id, { id: n.id, type: n.type, label: n.label, r, mass: r,
        x: W / 2 + Math.cos(ang) * rad, y: H / 2 + Math.sin(ang) * rad,
        vx: 0, vy: 0, fixed: false });
    });
    const links: SimLink[] = data.links
      .filter((l) => map.has(l.source) && map.has(l.target))
      .map((l) => ({ s: map.get(l.source)!, t: map.get(l.target)!,
        rest: l.kind === "live" ? 38 : l.kind === "sourced" ? 66 : 92 }));
    const adj = new Map<string, Set<string>>();
    for (const n of map.values()) adj.set(n.id, new Set([n.id]));
    for (const l of links) { adj.get(l.s.id)!.add(l.t.id); adj.get(l.t.id)!.add(l.s.id); }
    sim.current = { nodes: [...map.values()], links, adj };

    const step = () => {
      const s = sim.current!, a = alpha.current;
      for (const n of s.nodes) {
        if (n.fixed) continue;
        let fx = (W / 2 - n.x) * CENTER, fy = (H / 2 - n.y) * CENTER;
        for (const m of s.nodes) {
          if (m === n) continue;
          const dx = n.x - m.x, dy = n.y - m.y, d2 = dx * dx + dy * dy || 0.01;
          const f = (REPULSION * (m.r / 8)) / d2, d = Math.sqrt(d2);
          fx += (dx / d) * f; fy += (dy / d) * f;
        }
        n.vx = (n.vx + (fx / n.mass) * a) * DAMP;
        n.vy = (n.vy + (fy / n.mass) * a) * DAMP;
      }
      for (const l of s.links) {
        const dx = l.t.x - l.s.x, dy = l.t.y - l.s.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const f = (d - l.rest) * SPRING * a, ax = (dx / d) * f, ay = (dy / d) * f;
        if (!l.s.fixed) { l.s.vx += ax / l.s.mass; l.s.vy += ay / l.s.mass; }
        if (!l.t.fixed) { l.t.vx -= ax / l.t.mass; l.t.vy -= ay / l.t.mass; }
      }
      for (const n of s.nodes) {
        if (n.fixed) continue;
        n.vx = Math.max(-MAXV, Math.min(MAXV, n.vx));
        n.vy = Math.max(-MAXV, Math.min(MAXV, n.vy));
        n.x = Math.max(n.r, Math.min(W - n.r, n.x + n.vx));
        n.y = Math.max(n.r, Math.min(H - n.r, n.y + n.vy));
      }
      alpha.current += (0 - a) * ALPHA_DECAY; // cool toward 0 -> guaranteed settle
    };
    const paint = () => {
      const s = sim.current!;
      for (const n of s.nodes) {
        const el = gEls.current.get(n.id);
        if (el) el.setAttribute("transform", `translate(${n.x.toFixed(1)} ${n.y.toFixed(1)})`);
      }
      s.links.forEach((l, i) => {
        const el = lEls.current[i];
        if (el) {
          el.setAttribute("x1", l.s.x.toFixed(1)); el.setAttribute("y1", l.s.y.toFixed(1));
          el.setAttribute("x2", l.t.x.toFixed(1)); el.setAttribute("y2", l.t.y.toFixed(1));
        }
      });
    };
    const loop = () => {
      step(); paint();
      if (alpha.current < ALPHA_MIN && !drag.current) { running.current = false; return; }
      raf.current = requestAnimationFrame(loop);
    };
    kick.current = (a = 0.5) => {
      alpha.current = Math.max(alpha.current, a);
      if (!running.current && !reduce) {
        running.current = true; raf.current = requestAnimationFrame(loop);
      }
    };

    if (reduce) {
      alpha.current = 1;
      for (let i = 0; i < 300; i++) step();
      paint();
    } else {
      running.current = true; raf.current = requestAnimationFrame(loop);
    }
    return () => { cancelAnimationFrame(raf.current); running.current = false; };
  }, [data, reduce]);

  // --- drag: grab a node, throw it (release keeps velocity -> bounce) ---
  const toSvg = (e: React.PointerEvent) => {
    const rect = svgRef.current!.getBoundingClientRect();
    return { x: ((e.clientX - rect.left) / rect.width) * W,
             y: ((e.clientY - rect.top) / rect.height) * H };
  };
  const onDown = (e: React.PointerEvent, n: SimNode) => {
    e.preventDefault();
    (e.target as Element).setPointerCapture?.(e.pointerId);
    const p = toSvg(e);
    n.fixed = true; n.vx = 0; n.vy = 0; drag.current = { n, px: p.x, py: p.y };
    kick.current(0.6);
  };
  const onMove = (e: React.PointerEvent) => {
    const d = drag.current; if (!d) return;
    const p = toSvg(e);
    d.n.x = p.x; d.n.y = p.y;
    d.n.vx = (p.x - d.px) * 0.5; d.n.vy = (p.y - d.py) * 0.5;
    d.px = p.x; d.py = p.y;
    if (reduce) settlePaint();
  };
  const onUp = () => {
    const d = drag.current; if (!d) return;
    d.n.fixed = false; drag.current = null;
    kick.current(0.35); // let the thrown node's velocity ripple, then re-settle
  };
  const settlePaint = () => {
    const s = sim.current; if (!s) return;
    for (let k = 0; k < 30; k++) {
      for (const l of s.links) {
        const dx = l.t.x - l.s.x, dy = l.t.y - l.s.y, dd = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const f = (dd - l.rest) * SPRING;
        if (!l.s.fixed) { l.s.x += (dx / dd) * f; l.s.y += (dy / dd) * f; }
        if (!l.t.fixed) { l.t.x -= (dx / dd) * f; l.t.y -= (dy / dd) * f; }
      }
    }
    for (const n of s.nodes) {
      const el = gEls.current.get(n.id);
      if (el) el.setAttribute("transform", `translate(${n.x.toFixed(1)} ${n.y.toFixed(1)})`);
    }
    for (let i = 0; i < s.links.length; i++) {
      const el = lEls.current[i], l = s.links[i];
      if (el) {
        el.setAttribute("x1", l.s.x.toFixed(1)); el.setAttribute("y1", l.s.y.toFixed(1));
        el.setAttribute("x2", l.t.x.toFixed(1)); el.setAttribute("y2", l.t.y.toFixed(1));
      }
    }
  };

  const adj = sim.current?.adj;
  const isActive = (id: string) => !hover || (adj?.get(hover)?.has(id) ?? false);
  const setH = (id: string | null) => {
    setHover(id);
    onHover?.(id ? data.nodes.find((n) => n.id === id)?.label ?? null : null);
  };

  return (
    <svg ref={svgRef} className="fg" viewBox={`0 0 ${W} ${H}`}
      onPointerMove={onMove} onPointerUp={onUp} onPointerLeave={onUp}
      role="img" aria-label="interactive sourcing network — drag nodes; full data in the tables below">
      {data.links.map((l, i) => (
        <line key={i} ref={(el) => { lEls.current[i] = el; }}
          className={`fg-edge fg-e-${l.kind}${
            hover && !(isActive(l.source) && isActive(l.target)) ? " dim" : ""}`} />
      ))}
      {data.nodes.map((nn) => {
        const r = radius(nn.type, nn.size);
        const bigLabel = nn.type === "channel" || (nn.type === "investor" && r > 11);
        const showLabel = bigLabel || hover === nn.id
          || (hover != null && (adj?.get(hover)?.has(nn.id) ?? false));
        return (
          <g key={nn.id} className={`fg-node fg-${nn.type}${
            nn.live_only ? " fg-ch-live" : ""}${isActive(nn.id) ? "" : " dim"}`}
            ref={(el) => { if (el) gEls.current.set(nn.id, el); }}
            onPointerDown={(e) => {
              const sn = sim.current?.nodes.find((x) => x.id === nn.id);
              if (sn) onDown(e, sn);
            }}
            onPointerEnter={() => setH(nn.id)} onPointerLeave={() => setH(null)}>
            <title>{titleFor(nn)}</title>
            <circle r={r} />
            {showLabel && <text y={r + 10} textAnchor="middle">{nn.label}</text>}
          </g>
        );
      })}
    </svg>
  );
}

function titleFor(n: Network["nodes"][number]): string {
  if (n.type === "startup") return `${n.label} — ${n.sector} · ${n.outcome}`;
  if (n.type === "investor")
    return `${n.label} — backed ${n.backed?.length ?? n.size}: ${(n.backed || []).join(", ")}`;
  if (n.type === "founder")
    return `${n.label} — live pipeline · signal ${n.signal ?? "not yet scored"} · sourced via ${n.source}`;
  if (n.live_only)
    return `${n.label} — live scanner, no curated historical reference yet · ${n.size} founders sourced here`;
  return `${n.label} — sourced ${n.size} of these outcomes${n.covered_live ? " · we scan this channel live" : " · no live scanner"}`;
}
