import { useEffect, useMemo, useRef, useState } from "react";

// The living patient knowledge graph. A lightweight force simulation (no external
// libs) lays out fact nodes around a central patient node. Conflict / contradiction
// edges glow red. New nodes pop in as the graph "grows". This is Confide's memory,
// made visible.

const TYPE_STYLE = {
  patient: { color: "#eaf0ff", ring: "#2fe6c8", r: 34, icon: "🧑" },
  symptom: { color: "#ff9db0", ring: "#ff5a6e", r: 22, icon: "＋" },
  condition: { color: "#ffd08a", ring: "#ffb84d", r: 22, icon: "◆" },
  allergy: { color: "#ff8f8f", ring: "#ff5a6e", r: 24, icon: "⚠" },
  medication: { color: "#8fd0ff", ring: "#5b8cff", r: 24, icon: "℞" },
  procedure: { color: "#c4b5fd", ring: "#a78bfa", r: 22, icon: "✚" },
  lab_order: { color: "#9becd8", ring: "#2fe6c8", r: 22, icon: "🧪" },
  vital: { color: "#b9c4e6", ring: "#6b779c", r: 20, icon: "♥" },
  statement: { color: "#d8def0", ring: "#8a97bd", r: 20, icon: "❝" },
};

function styleFor(t) {
  return TYPE_STYLE[t] || TYPE_STYLE.statement;
}

export default function GraphView({ snapshot, height = 460, onSelect }) {
  const wrapRef = useRef(null);
  const [size, setSize] = useState({ w: 800, h: height });
  const [sel, setSel] = useState(null);
  const simRef = useRef({ nodes: [], edges: [] });
  const [, force] = useState(0);
  const rafRef = useRef(null);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: height }));
    ro.observe(el);
    setSize({ w: el.clientWidth, h: height });
    return () => ro.disconnect();
  }, [height]);

  // Which node ids are implicated in an active alert (for the red glow).
  const alertNodeIds = useMemo(() => {
    const s = new Set();
    (snapshot?.alerts || []).forEach((a) => {
      if (a.status === "dismissed") return;
      try {
        JSON.parse(a.node_ids || "[]").forEach((id) => s.add(id));
      } catch { /* noop */ }
    });
    return s;
  }, [snapshot]);

  // Build / reconcile the simulation when the snapshot changes, preserving
  // positions of nodes we already have (so it doesn't jump on updates).
  useEffect(() => {
    const cx = size.w / 2;
    const cy = size.h / 2;
    const prev = new Map(simRef.current.nodes.map((n) => [n.key, n]));

    const simNodes = [{ key: "patient", id: "patient", type: "patient", label: "Patient", pinned: true, x: cx, y: cy }];
    (snapshot?.nodes || []).forEach((n, i) => {
      const key = "n" + n.id;
      const p = prev.get(key);
      const angle = (i / Math.max(1, (snapshot.nodes || []).length)) * Math.PI * 2;
      simNodes.push({
        key,
        id: n.id,
        type: n.ntype,
        label: n.label,
        node: n,
        isNew: !p,
        x: p ? p.x : cx + Math.cos(angle) * 150 + (Math.random() - 0.5) * 40,
        y: p ? p.y : cy + Math.sin(angle) * 150 + (Math.random() - 0.5) * 40,
        vx: 0,
        vy: 0,
      });
    });

    const byId = new Map(simNodes.map((n) => [n.id, n]));
    const simEdges = [];
    // every fact links to the patient (spokes)
    simNodes.forEach((n) => {
      if (n.id !== "patient") simEdges.push({ a: "patient", b: n.id, rel: "spoke" });
    });
    (snapshot?.edges || []).forEach((e) => {
      if (byId.has(e.src_node_id) && byId.has(e.dst_node_id)) {
        simEdges.push({ a: e.src_node_id, b: e.dst_node_id, rel: e.relation });
      }
    });

    simRef.current = { nodes: simNodes, edges: simEdges };
    startSim();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshot, size.w, size.h]);

  function startSim() {
    cancelAnimationFrame(rafRef.current);
    let ticks = 0;
    const step = () => {
      const { nodes, edges } = simRef.current;
      const cx = size.w / 2;
      const cy = size.h / 2;
      // repulsion
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          let dx = a.x - b.x;
          let dy = a.y - b.y;
          let d2 = dx * dx + dy * dy || 0.01;
          const rep = 9000 / d2;
          const d = Math.sqrt(d2);
          const fx = (dx / d) * rep;
          const fy = (dy / d) * rep;
          if (!a.pinned) { a.vx += fx; a.vy += fy; }
          if (!b.pinned) { b.vx -= fx; b.vy -= fy; }
        }
      }
      // springs
      const byId = new Map(nodes.map((n) => [n.id, n]));
      edges.forEach((e) => {
        const a = byId.get(e.a);
        const b = byId.get(e.b);
        if (!a || !b) return;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const target = e.rel === "spoke" ? 135 : 90;
        const k = e.rel === "spoke" ? 0.008 : 0.02;
        const f = (d - target) * k;
        const fx = (dx / d) * f;
        const fy = (dy / d) * f;
        if (!a.pinned) { a.vx += fx; a.vy += fy; }
        if (!b.pinned) { b.vx -= fx; b.vy -= fy; }
      });
      // integrate + centering + damping
      nodes.forEach((n) => {
        if (n.pinned) { n.x = cx; n.y = cy; return; }
        n.vx += (cx - n.x) * 0.0015;
        n.vy += (cy - n.y) * 0.0015;
        n.vx *= 0.82;
        n.vy *= 0.82;
        n.x += n.vx;
        n.y += n.vy;
        const pad = 40;
        n.x = Math.max(pad, Math.min(size.w - pad, n.x));
        n.y = Math.max(pad, Math.min(size.h - pad, n.y));
      });
      force((v) => v + 1);
      ticks++;
      if (ticks < 240) rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);
  }

  useEffect(() => () => cancelAnimationFrame(rafRef.current), []);

  const { nodes, edges } = simRef.current;
  const byId = new Map(nodes.map((n) => [n.id, n]));

  function pick(n) {
    setSel(n.id === sel ? null : n.id);
    if (onSelect && n.node) onSelect(n.node);
  }

  return (
    <div ref={wrapRef} style={{ position: "relative", width: "100%" }}>
      <svg width={size.w} height={size.h} style={{ display: "block" }}>
        <defs>
          <radialGradient id="glowTeal" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(47,230,200,0.35)" />
            <stop offset="100%" stopColor="rgba(47,230,200,0)" />
          </radialGradient>
        </defs>
        {/* edges */}
        {edges.map((e, i) => {
          const a = byId.get(e.a);
          const b = byId.get(e.b);
          if (!a || !b) return null;
          const conflict = e.rel === "conflicts_with" || e.rel === "contradicts";
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={conflict ? "var(--crit)" : e.rel === "spoke" ? "rgba(90,140,255,0.14)" : "rgba(167,139,250,0.4)"}
              strokeWidth={conflict ? 2.4 : 1.2}
              strokeDasharray={conflict ? "5 4" : e.rel === "contradicts" ? "2 3" : "0"}
              style={conflict ? { animation: "dash 0.8s linear infinite" } : undefined}
            />
          );
        })}
        {/* nodes */}
        {nodes.map((n) => {
          const s = styleFor(n.type);
          const flagged = n.id !== "patient" && alertNodeIds.has(n.id);
          const unconfirmed = n.node && n.node.status === "unconfirmed";
          const denied = n.node && n.node.polarity === "denied";
          return (
            <g
              key={n.key}
              transform={`translate(${n.x},${n.y})`}
              style={{
                cursor: "pointer",
                animation: n.isNew ? "nodePop 0.5s ease both" : undefined,
              }}
              onClick={() => pick(n)}
            >
              {(flagged || n.type === "patient") && <circle r={s.r + 16} fill="url(#glowTeal)" opacity={n.type === "patient" ? 0.9 : 0} />}
              {flagged && <circle r={s.r + 8} fill="none" stroke="var(--crit)" strokeWidth="2" opacity="0.9" style={{ animation: "pulseRing 1.2s ease-out infinite" }} />}
              <circle
                r={s.r}
                fill={n.type === "patient" ? "#0f1830" : "var(--panel)"}
                stroke={flagged ? "var(--crit)" : s.ring}
                strokeWidth={n.type === "patient" ? 3 : sel === n.id ? 3 : 1.8}
                strokeDasharray={unconfirmed ? "4 3" : "0"}
                opacity={denied ? 0.65 : 1}
              />
              <text textAnchor="middle" dy="5" fontSize={n.type === "patient" ? 20 : 15} fill={s.color}>
                {s.icon}
              </text>
              {n.type !== "patient" && (
                <text
                  textAnchor="middle"
                  y={s.r + 15}
                  fontSize="11"
                  fill="var(--text-dim)"
                  style={{ pointerEvents: "none" }}
                >
                  {n.label.length > 22 ? n.label.slice(0, 20) + "…" : n.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <style>{`
        @keyframes dash { to { stroke-dashoffset: -18; } }
        @keyframes pulseRing { 0% { transform: scale(0.85); opacity: 0.9; } 100% { transform: scale(1.3); opacity: 0; } }
      `}</style>
    </div>
  );
}
