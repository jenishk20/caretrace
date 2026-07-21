import { useEffect, useState } from "react";
import { api } from "../api";

export default function RoiView({ pid }) {
  const [roi, setRoi] = useState(null);
  useEffect(() => { api.patientRoi(pid).then(setRoi).catch(() => setRoi(null)); }, [pid]);
  if (!roi) return <div className="card" style={{ padding: 20 }}><span className="spinner" /></div>;
  const metrics = [
    ["Documentation", `${roi.documentation_minutes_saved_estimate} min`, "estimated time saved"],
    ["Coding", `$${roi.coding_revenue_captured_estimate_usd}`, "nominal estimate, not reimbursement"],
    ["Near-misses", roi.near_misses_prevented, "critical Guardian catches"],
    ["Throughput", roi.runs_per_shift, "runs in demo shift"],
    ["Avg latency", `${(roi.avg_latency_ms / 1000).toFixed(1)}s`, "local end-to-end"],
  ];
  return <div><div className="eyebrow">Local workflow analytics</div><h1 style={{ margin: "4px 0 18px" }}>ROI & safety proof</h1><div className="roi-grid">{metrics.map(([label, value, caption]) => <div className="card roi-card" key={label}><span>{label}</span><strong>{value}</strong><small>{caption}</small></div>)}</div><div className="card roi-method"><b>Conservative methodology</b>{Object.values(roi.methodology || {}).map((line) => <p key={line}>{line}</p>)}</div><style>{`.roi-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}.roi-card{padding:18px;display:flex;flex-direction:column}.roi-card span{color:var(--text-mute);font-size:11px;text-transform:uppercase;letter-spacing:.08em}.roi-card strong{font-size:26px;color:var(--teal);margin:8px 0}.roi-card small{color:var(--text-mute)}.roi-method{margin-top:16px;padding:18px}.roi-method p{font-size:12px;color:var(--text-dim);margin-top:5px}@media(max-width:1000px){.roi-grid{grid-template-columns:repeat(2,1fr)}}`}</style></div>;
}
