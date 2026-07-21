import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

// A deterministic constellation rather than a live force simulation: fact positions
// remain stable as a responsive layout changes, so every node and Guardian edge stays
// visible and clickable.
const TYPE_STYLE = {
  patient: { color: "#eafcff", ring: "#64e8d2", r: 36, icon: "✦" },
  symptom: { color: "#ffb0bc", ring: "#ff6f82", r: 22, icon: "+" },
  condition: { color: "#ffd995", ring: "#f7c86f", r: 22, icon: "◆" },
  allergy: { color: "#ffaaa9", ring: "#ff6f82", r: 24, icon: "!" },
  medication: { color: "#a5d8ff", ring: "#76a9ff", r: 24, icon: "℞" },
  procedure: { color: "#d4c5ff", ring: "#b29bff", r: 22, icon: "✚" },
  lab_order: { color: "#aaf3de", ring: "#64e8d2", r: 22, icon: "⌁" },
  vital: { color: "#c8d3eb", ring: "#8da0bf", r: 20, icon: "♥" },
  statement: { color: "#d8e1f4", ring: "#98a7c4", r: 20, icon: "“" },
};

const styleFor = (type) => TYPE_STYLE[type] || TYPE_STYLE.statement;
const short = (text, length = 21) => (text || "").length > length ? `${text.slice(0, length - 1)}…` : text;
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

export default function GraphView({ snapshot, height = 460, onSelect }) {
  const wrapRef = useRef(null);
  const [size, setSize] = useState({ w: 760, h: height });
  const [selectedId, setSelectedId] = useState(null);
  const [expanded, setExpanded] = useState(false);

  useLayoutEffect(() => {
    const element = wrapRef.current;
    if (!element) return undefined;
    const measure = () => {
      const w = expanded ? Math.min(1180, Math.round(window.innerWidth * 0.9)) : element.clientWidth;
      const h = expanded ? Math.round(window.innerHeight * 0.78) : height;
      if (w > 0) setSize({ w, h });
    };
    const observer = new ResizeObserver(measure);
    observer.observe(element); measure();
    window.addEventListener("resize", measure);
    return () => { observer.disconnect(); window.removeEventListener("resize", measure); };
  }, [expanded, height]);

  useEffect(() => {
    if (!expanded) return undefined;
    const close = (event) => event.key === "Escape" && setExpanded(false);
    const oldOverflow = document.body.style.overflow;
    window.addEventListener("keydown", close); document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", close); document.body.style.overflow = oldOverflow; };
  }, [expanded]);

  const graph = useMemo(() => {
    const facts = snapshot?.nodes || [];
    const cx = size.w / 2; const cy = size.h / 2;
    const minSide = Math.min(size.w, size.h);
    const innerRadius = clamp(minSide * 0.25, 105, 170);
    const outerRadius = clamp(minSide * 0.39, 155, 265);
    const nodes = [{ key: "patient", id: "patient", type: "patient", label: "Patient", x: cx, y: cy }];
    facts.forEach((fact, index) => {
      const onInnerRing = index < 8;
      const ringCount = onInnerRing ? Math.min(8, facts.length) : Math.max(1, facts.length - 8);
      const ringIndex = onInnerRing ? index : index - 8;
      const angle = -Math.PI / 2 + (ringIndex / ringCount) * Math.PI * 2 + (onInnerRing ? 0 : Math.PI / ringCount);
      const radius = onInnerRing ? innerRadius : outerRadius;
      const style = styleFor(fact.ntype);
      const padding = style.r + 24;
      nodes.push({ key: `node-${fact.id}`, id: fact.id, type: fact.ntype, label: fact.label, node: fact,
        x: clamp(cx + Math.cos(angle) * radius, padding, size.w - padding),
        y: clamp(cy + Math.sin(angle) * radius, padding, size.h - padding) });
    });
    const byId = new Map(nodes.map((node) => [node.id, node]));
    const edges = facts.map((fact) => ({ a: "patient", b: fact.id, relation: "recorded" }));
    (snapshot?.edges || []).forEach((edge) => {
      if (byId.has(edge.src_node_id) && byId.has(edge.dst_node_id)) edges.push({ a: edge.src_node_id, b: edge.dst_node_id, relation: edge.relation });
    });
    const flagged = new Set();
    (snapshot?.alerts || []).filter((alert) => alert.status !== "dismissed").forEach((alert) => {
      try { JSON.parse(alert.node_ids || "[]").forEach((id) => flagged.add(id)); } catch { /* malformed legacy data */ }
    });
    return { nodes, edges, byId, flagged };
  }, [snapshot, size]);

  const pick = (node) => {
    if (node.id === "patient") return;
    setSelectedId((current) => current === node.id ? null : node.id);
    onSelect?.(node.node);
  };

  return (
    <div className={expanded ? "gv-overlay" : "gv-shell"} onClick={expanded ? () => setExpanded(false) : undefined}>
      <div ref={wrapRef} className="gv-stage" onClick={expanded ? (event) => event.stopPropagation() : undefined}>
        <button className="gv-expand" onClick={() => setExpanded((current) => !current)}>{expanded ? "✕ Close graph" : "⤢ Expand graph"}</button>
        <svg viewBox={`0 0 ${size.w} ${size.h}`} width={size.w} height={size.h} role="img" aria-label="Evidence-linked patient fact graph">
          <defs>
            <radialGradient id="patientHalo"><stop stopColor="#64e8d2" stopOpacity=".28" /><stop offset="1" stopColor="#64e8d2" stopOpacity="0" /></radialGradient>
            <filter id="nodeShadow" x="-60%" y="-60%" width="220%" height="220%"><feDropShadow dx="0" dy="6" stdDeviation="6" floodColor="#000" floodOpacity=".38" /></filter>
          </defs>
          <circle cx={size.w / 2} cy={size.h / 2} r={Math.min(size.w, size.h) * 0.42} fill="none" stroke="rgba(100,232,210,.09)" strokeDasharray="3 8" />
          <circle cx={size.w / 2} cy={size.h / 2} r={Math.min(size.w, size.h) * 0.27} fill="none" stroke="rgba(118,169,255,.1)" />
          {graph.edges.map((edge, index) => {
            const a = graph.byId.get(edge.a); const b = graph.byId.get(edge.b);
            if (!a || !b) return null;
            const conflict = edge.relation === "conflicts_with" || edge.relation === "contradicts";
            return <line key={`${edge.a}-${edge.b}-${index}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
              stroke={conflict ? "#ff6f82" : edge.relation === "recorded" ? "rgba(118,169,255,.21)" : "rgba(178,155,255,.64)"}
              strokeWidth={conflict ? "2.6" : edge.relation === "recorded" ? "1" : "1.8"}
              strokeDasharray={conflict ? "6 5" : undefined} className={conflict ? "gv-conflict" : undefined} />;
          })}
          {graph.nodes.map((node) => {
            const style = styleFor(node.type); const isPatient = node.id === "patient";
            const flagged = graph.flagged.has(node.id); const selected = selectedId === node.id;
            const unconfirmed = node.node?.status === "unconfirmed"; const denied = node.node?.polarity === "denied";
            return <g key={node.key} transform={`translate(${node.x},${node.y})`} className="gv-node" onClick={() => pick(node)}>
              <title>{isPatient ? "Patient record" : `${node.label}${flagged ? " — requires clinician review" : ""}`}</title>
              {isPatient && <circle r={style.r + 24} fill="url(#patientHalo)" />}
              {flagged && <circle r={style.r + 9} fill="none" stroke="#ff6f82" strokeWidth="1.5" className="gv-alert-ring" />}
              <circle r={style.r} fill={isPatient ? "#123949" : "#102430"} stroke={flagged ? "#ff6f82" : style.ring}
                strokeWidth={isPatient || selected ? "3" : "1.8"} strokeDasharray={unconfirmed ? "4 3" : undefined} opacity={denied ? ".65" : "1"} filter="url(#nodeShadow)" />
              <text textAnchor="middle" dy={isPatient ? "7" : "5"} fontSize={isPatient ? "20" : "15"} fill={style.color}>{style.icon}</text>
              {!isPatient && <text textAnchor="middle" y={style.r + 16} fontSize="11" fill="#c5d6e5" className="gv-label">{short(node.label)}</text>}
            </g>;
          })}
          {graph.nodes.length === 1 && <text x={size.w / 2} y={size.h - 30} textAnchor="middle" fill="#91a7b9" fontSize="13">Confirmed facts will appear here after a clinician review.</text>}
        </svg>
      </div>
      <style>{`
        .gv-shell { position:relative; min-height:140px; }
        .gv-stage { position:relative; width:100%; overflow:hidden; border-radius:14px; background:radial-gradient(circle at 50% 48%,rgba(26,75,88,.35),rgba(5,19,28,.12) 62%); }
        .gv-stage svg { display:block; max-width:100%; }
        .gv-node { cursor:pointer; transform-origin:center; transition:opacity .16s ease; }
        .gv-node:hover circle { filter:brightness(1.25); }
        .gv-label { pointer-events:none; paint-order:stroke; stroke:#081721; stroke-width:3px; stroke-linejoin:round; }
        .gv-expand { position:absolute; top:10px; right:10px; z-index:3; padding:7px 10px; border-radius:9px; background:rgba(7,25,35,.88); border:1px solid var(--line); color:var(--text-dim); font-size:12px; }
        .gv-expand:hover { border-color:var(--teal-dim); color:var(--text); }
        .gv-overlay { position:fixed; inset:0; z-index:90; padding:24px; display:grid; place-items:center; background:rgba(3,12,18,.88); backdrop-filter:blur(12px); }
        .gv-overlay .gv-stage { width:min(1180px,90vw); max-width:90vw; box-shadow:var(--shadow-lg); border:1px solid var(--line); }
        .gv-conflict { animation:gvDash 1s linear infinite; }
        .gv-alert-ring { animation:gvPulse 1.4s ease-out infinite; }
        @keyframes gvDash { to { stroke-dashoffset:-22; } }
        @keyframes gvPulse { 0% { opacity:1; transform:scale(.86); } 100% { opacity:0; transform:scale(1.3); } }
      `}</style>
    </div>
  );
}
