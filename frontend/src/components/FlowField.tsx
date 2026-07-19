import { useEffect, useRef } from "react";

/* The generative light-field behind the landing hero. Particles ride a smooth,
   near-horizontal flow field (summed-sine pseudo-noise, no deps) and each keeps a
   position history drawn as one long polyline — so the surface reads as streams
   of signal flowing rightward and converging, the product's whole thesis rendered.
   The canvas is cleared and redrawn each frame (no accumulation runaway); overlap
   of many strands under 'lighter' compositing is what makes the bundle glow.
   Brightness is weighted to the right so the left stays near-black and the
   headline keeps AA. Honors prefers-reduced-motion with one static frame.
   DPR-aware, pauses when hidden, cleans up on unmount. */

const BLUE = [
  [120, 170, 255],
  [95, 145, 255],
  [150, 195, 255],
  [78, 125, 250],
];
const TAIL = 64; // points of history per strand

export default function FlowField() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: false });
    if (!ctx) return;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let W = 0, H = 0;

    type P = { x: number; y: number; life: number; max: number; c: number[]; w: number; node: boolean; xs: number[]; ys: number[] };
    let parts: P[] = [];
    let raf = 0;
    let t = 0;

    // Near-horizontal flow: cos(angle) stays > 0 so every strand drifts right;
    // the sine terms give the vertical rise/fall of long aurora ribbons.
    const field = (x: number, y: number, time: number) => {
      const nx = x * 0.0021, ny = y * 0.0038;
      const a =
        Math.sin(nx + ny + time) * 0.55 +
        Math.sin(ny * 1.7 - time * 0.55) * 0.34 +
        Math.sin(nx * 0.5 + time * 0.3) * 0.16;
      return a - 0.16; // slight upward bias → streams rise toward the top-right
    };

    const reset = (p: P) => {
      p.x = (Math.random() * 1.2 - 0.15) * W;
      p.y = Math.random() * H;
      p.life = 0;
      p.max = 260 + Math.random() * 520;
      p.c = BLUE[(Math.random() * BLUE.length) | 0];
      p.w = Math.random() < 0.22 ? 1.5 : 0.75;
      p.node = Math.random() < 0.05;
      p.xs.length = 0; p.ys.length = 0;
    };

    const resize = () => {
      W = canvas.clientWidth;
      H = canvas.clientHeight;
      canvas.width = Math.max(1, Math.round(W * dpr));
      canvas.height = Math.max(1, Math.round(H * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      const count = Math.min(300, Math.round((W * H) / 6200));
      parts = Array.from({ length: count }, () => {
        const p: P = { x: 0, y: 0, life: 0, max: 0, c: BLUE[0], w: 1, node: false, xs: [], ys: [] };
        reset(p);
        // stagger initial ages so strands aren't all born together
        p.life = (Math.random() * p.max) | 0;
        return p;
      });
    };

    const advance = (p: P) => {
      const ang = field(p.x, p.y, t);
      const speed = 2.1 + p.w * 1.1;
      p.x += Math.cos(ang) * speed;
      p.y += Math.sin(ang) * speed;
      p.life++;
      p.xs.push(p.x); p.ys.push(p.y);
      if (p.xs.length > TAIL) { p.xs.shift(); p.ys.shift(); }
      if (p.life > p.max || p.x > W + 40 || p.y < -40 || p.y > H + 40) reset(p);
    };

    const draw = (p: P) => {
      const n = p.xs.length;
      if (n < 2) return;
      // fade in over birth, out toward death; darken toward the left edge.
      const fade = Math.min(1, p.life / 40) * Math.min(1, (p.max - p.life) / 60);
      const edge = Math.pow(Math.min(1, p.x / W / 0.5 + 0.05), 1.7);
      const alpha = fade * edge;
      if (alpha < 0.015) return;
      const [r, g, b] = p.c;
      ctx.strokeStyle = `rgba(${r},${g},${b},${alpha})`;
      ctx.lineWidth = p.w;
      ctx.beginPath();
      ctx.moveTo(p.xs[0], p.ys[0]);
      for (let i = 1; i < n; i++) ctx.lineTo(p.xs[i], p.ys[i]);
      ctx.stroke();
      if (p.node) {
        ctx.shadowBlur = 10;
        ctx.shadowColor = `rgba(${r},${g},${b},${alpha})`;
        ctx.fillStyle = `rgba(190,215,255,${alpha})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 1 + p.w, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }
    };

    const frame = () => {
      ctx.globalCompositeOperation = "source-over";
      ctx.fillStyle = "#05070e";
      ctx.fillRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      t += 0.0018;
      for (const p of parts) { advance(p); draw(p); }
      raf = requestAnimationFrame(frame);
    };

    resize();

    if (reduce) {
      ctx.fillStyle = "#05070e";
      ctx.fillRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      for (let i = 0; i < TAIL + 40; i++) { t += 0.0018; for (const p of parts) advance(p); }
      for (const p of parts) draw(p);
    } else {
      raf = requestAnimationFrame(frame);
    }

    const ro = new ResizeObserver(() => resize());
    ro.observe(canvas);
    const onVis = () => {
      if (document.hidden) cancelAnimationFrame(raf);
      else if (!reduce) raf = requestAnimationFrame(frame);
    };
    document.addEventListener("visibilitychange", onVis);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      document.removeEventListener("visibilitychange", onVis);
    };
  }, []);

  return <canvas ref={ref} className="flowfield" aria-hidden="true" />;
}
