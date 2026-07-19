import { useEffect, useRef, useState } from "react";
import type { Network } from "../api";

/* A hand-rolled force-directed graph — no charting library (per DESIGN.md).
   Repulsion + spring + centering physics with light damping, so it settles into
   clusters but springs to life when you drag a node (grab and throw it — the
   whole cluster bounces). Node RADIUS encodes influence: sourcing channels by how
   many outcomes they produced, funds by how many they backed, startups by outcome
   tier. Positions are mutated imperatively each frame (refs, not React state) so it
   holds 60fps; only hover highlight goes through React. Respects reduced-motion:
   it settles instantly and skips the animation loop. */

interface SimNode {
  id: string; type: string; label: string; r: number; mass: number;
  x: number; y: number; vx: number; vy: number; fixed: boolean;
}
interface SimLink { s: SimNode; t: SimNode; rest: number; }

const W = 780, H = 560;
const REPULSION = 1400, SPRING = 0.028, CENTER = 0.0032, DAMP = 0.9, MAXV = 18;

function radius(type: string, size: number): number {
  if (type === "channel") return 11 + Math.sqrt(size) * 3.4;
  if (type === "investor") return 5 + Math.sqrt(size) * 2.6;
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
  const [hover, setHover] = useState<string | null>(null);
  const reduce = typeof matchMedia !== "undefined"
    && matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Build the simulation once from the graph payload.
  useEffect(() => {
    const map = new Map<string, SimNode>();
    data.nodes.forEach((n, i) => {
      const ang = (i / data.nodes.length) * Math.PI * 2;
      const rad = 60 + Math.random() * 150;
      map.set(n.id, {
        id: n.id, type: n.type, label: n.label,
        r: radius(n.type, n.size), mass: radius(n.type, n.size),
        x: W / 2 + Math.cos(ang) * rad, y: H / 2 + Math.sin(ang) * rad,
        vx: 0, vy: 0, fixed: false,
      });
    });
    const links: SimLink[] = data.links
      .filter((l) => map.has(l.source) && map.has(l.target))
      .map((l) => ({ s: map.get(l.source)!, t: map.get(l.target)!,
        rest: l.kind === "sourced" ? 66 : 92 }));
    const adj = new Map<string, Set<string>>();
    for (const n of map.values()) adj.set(n.id, new Set([n.id]));
    for (const l of links) { adj.get(l.s.id)!.add(l.t.id); adj.get(l.t.id)!.add(l.s.id); }
    sim.current = { nodes: [...map.values()], links, adj };

    const step = () => {
      const s = sim.current!;
      for (const n of s.nodes) {
        if (n.fixed) continue;
        let fx = (W / 2 - n.x) * CENTER, fy = (H / 2 - n.y) * CENTER;
        for (const m of s.nodes) {
          if (m === n) continue;
          let dx = n.x - m.x, dy = n.y - m.y;
          let d2 = dx * dx + dy * dy || 0.01;
          const f = (REPULSION * (m.r / 8)) / d2;
          const d = Math.sqrt(d2);
          fx += (dx / d) * f; fy += (dy / d) * f;
        }
        n.vx = (n.vx + fx / n.mass) * DAMP;
        n.vy = (n.vy + fy / n.mass) * DAMP;
      }
      for (const l of s.links) {
        let dx = l.t.x - l.s.x, dy = l.t.y - l.s.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const f = (d - l.rest) * SPRING;
        const ax = (dx / d) * f, ay = (dy / d) * f;
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
      paint();
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

    if (reduce) {
      for (let i = 0; i < 400; i++) step();  // settle synchronously, no animation
      paint();
    } else {
      const loop = () => { step(); raf.current = requestAnimationFrame(loop); };
      raf.current = requestAnimationFrame(loop);
    }
    return () => cancelAnimationFrame(raf.current);
  }, [data, reduce]);

  // --- drag: grab a node, throw it (release keeps velocity -> bounce) ---
  const toSvg = (e: React.PointerEvent | PointerEvent) => {
    const rect = svgRef.current!.getBoundingClientRect();
    return { x: ((e.clientX - rect.left) / rect.width) * W,
             y: ((e.clientY - rect.top) / rect.height) * H };
  };
  const onDown = (e: React.PointerEvent, n: SimNode) => {
    e.preventDefault();
    (e.target as Element).setPointerCapture?.(e.pointerId);
    const p = toSvg(e);
    n.fixed = true; drag.current = { n, px: p.x, py: p.y };
  };
  const onMove = (e: React.PointerEvent) => {
    if (!drag.current) return;
    const p = toSvg(e), d = drag.current;
    d.n.x = p.x; d.n.y = p.y;
    d.n.vx = (p.x - d.px) * 0.6; d.n.vy = (p.y - d.py) * 0.6; // carry throw velocity
    d.px = p.x; d.py = p.y;
    if (reduce) { for (let i = 0; i < 40; i++) settleOnce(); }
  };
  const onUp = () => {
    if (drag.current) { drag.current.n.fixed = false; drag.current = null; }
  };
  const settleOnce = () => {
    // minimal re-settle used only in reduced-motion drag (no rAF running)
    const s = sim.current; if (!s) return;
    for (const l of s.links) {
      let dx = l.t.x - l.s.x, dy = l.t.y - l.s.y;
      const dd = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const f = (dd - l.rest) * SPRING;
      if (!l.s.fixed) { l.s.x += (dx / dd) * f; l.s.y += (dy / dd) * f; }
      if (!l.t.fixed) { l.t.x -= (dx / dd) * f; l.t.y -= (dy / dd) * f; }
    }
    for (const n of s.nodes) {
      const el = gEls.current.get(n.id);
      if (el) el.setAttribute("transform", `translate(${n.x.toFixed(1)} ${n.y.toFixed(1)})`);
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
          className={`fg-edge ${l.kind === "sourced" ? "fg-e-src" : "fg-e-seed"}${
            hover && !(isActive(l.source) && isActive(l.target)) ? " dim" : ""}`} />
      ))}
      {/* Render from data.nodes (available on first paint); physics moves them via
          refs. Handlers look up the matching mutable sim node by id. */}
      {data.nodes.map((nn) => {
        const r = radius(nn.type, nn.size);
        const bigLabel = nn.type === "channel" || (nn.type === "investor" && r > 11);
        const showLabel = bigLabel || hover === nn.id
          || (hover != null && (adj?.get(hover)?.has(nn.id) ?? false));
        return (
          <g key={nn.id} className={`fg-node fg-${nn.type}${isActive(nn.id) ? "" : " dim"}`}
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
  if (n.type === "startup")
    return `${n.label} — ${n.sector} · ${n.outcome}`;
  if (n.type === "investor")
    return `${n.label} — backed ${n.backed?.length ?? n.size}: ${(n.backed || []).join(", ")}`;
  return `${n.label} — sourced ${n.size} of these outcomes${n.covered_live ? " · we scan this channel live" : " · no live scanner"}`;
}
