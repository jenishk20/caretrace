import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { session } from "../lib/session.js";
import NetworkPill from "../components/NetworkPill.jsx";
import GemmaConsole from "../components/GemmaConsole.jsx";
import VisitFlow from "../views/VisitFlow.jsx";
import Overview from "../views/Overview.jsx";
import ScribeView from "../views/ScribeView.jsx";
import VisitsView from "../views/VisitsView.jsx";
import ConsentView from "../views/ConsentView.jsx";
import DischargeView from "../views/DischargeView.jsx";
import HandoffView from "../views/HandoffView.jsx";

const NAV = [
  { key: "visit", label: "Guided visit", icon: "🧭", hint: "Onboard → discharge" },
  { key: "dashboard", label: "Dashboard", icon: "🗂", hint: "Everything, one place" },
  { key: "overview", label: "Overview", icon: "◈", hint: "Graph & Guardian" },
  { key: "scribe", label: "Scribe", icon: "🎧", hint: "Capture a round" },
  { key: "consent", label: "Consent", icon: "📋", hint: "Explain a form" },
  { key: "discharge", label: "Discharge", icon: "🏠", hint: "Going-home plan" },
  { key: "handoff", label: "Handoff", icon: "🔀", hint: "SBAR & catch-up" },
];

export default function Workspace() {
  const { id } = useParams();
  const pid = Number(id);
  const nav = useNavigate();
  const staff = session.staff();
  const [tab, setTab] = useState("visit");
  const [patient, setPatient] = useState(null);
  const [snapshot, setSnapshot] = useState({ nodes: [], edges: [], alerts: [] });

  const refresh = useCallback(async () => {
    const [p, snap] = await Promise.all([api.getPatient(pid), api.getGraph(pid)]);
    setPatient(p);
    setSnapshot(snap);
  }, [pid]);

  useEffect(() => { refresh().catch(() => {}); }, [refresh]);

  const activeAlerts = (snapshot.alerts || []).filter((a) => a.status === "active");

  // Shared bedside device: lock every clinical view (clears the staff session so
  // RequireStaff bounces back to login) and hand the device to the patient's view.
  function handToPatient() {
    if (!confirm("Hand this device to the patient? The clinical view will lock — sign in again to return.")) return;
    session.clearStaff();
    nav(session.patient() ? "/patient" : "/patient/login");
  }

  if (!patient) return <div style={{ display: "grid", placeItems: "center", height: "100vh" }}><span className="spinner" /></div>;

  const shared = { patient, pid, staff, snapshot, refresh, setTab };

  return (
    <div className="ws">
      <aside className="ws-side">
        <div className="row" style={{ gap: 10, padding: "4px 8px 20px" }}>
          <span style={{ color: "var(--teal)", fontSize: 20 }}>◈</span>
          <b>Confide</b>
        </div>
        <button className="side-back" onClick={() => nav("/doctor")}>← All patients</button>
        <div className="side-pt">
          <div className="avatar">{patient.name.split(" ").map((w) => w[0]).slice(0, 2).join("")}</div>
          <div>
            <div style={{ fontWeight: 700 }}>{patient.name}</div>
            <div className="muted" style={{ fontSize: 12 }}>{patient.age} yrs · Room {patient.room || "—"}</div>
          </div>
        </div>
        <nav>
          {NAV.map((n) => (
            <button key={n.key} className={`side-item ${tab === n.key ? "on" : ""}`} onClick={() => setTab(n.key)}>
              <span className="si-icon">{n.icon}</span>
              <span>
                <div className="si-label">{n.label}</div>
                <div className="si-hint">{n.hint}</div>
              </span>
              {(n.key === "overview" || n.key === "visit") && activeAlerts.length > 0 && (
                <span className="si-badge">{activeAlerts.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="grow" />
        <div className="side-foot">
          <button className="hand-off" onClick={handToPatient} title="Lock the clinical view and give the device to the patient">
            🤝 Hand to patient
          </button>
          <NetworkPill />
        </div>
      </aside>

      <main className="ws-main">
        {tab === "visit" && <VisitFlow {...shared} />}
        {tab === "dashboard" && <VisitsView {...shared} />}
        {tab === "overview" && <Overview {...shared} />}
        {tab === "scribe" && <ScribeView {...shared} />}
        {tab === "consent" && <ConsentView {...shared} />}
        {tab === "discharge" && <DischargeView {...shared} />}
        {tab === "handoff" && <HandoffView {...shared} />}
      </main>

      <GemmaConsole />

      <style>{`
        .ws { display:grid; grid-template-columns:260px 1fr; min-height:100vh; }
        .ws-side { border-right:1px solid var(--line); padding:20px 16px; display:flex; flex-direction:column;
          position:sticky; top:0; height:100vh; background:var(--bg-soft); }
        .side-back { text-align:left; color:var(--text-mute); font-size:13px; padding:6px 8px; margin-bottom:14px; }
        .side-back:hover { color:var(--teal); }
        .side-pt { display:flex; gap:12px; align-items:center; padding:14px; background:var(--panel);
          border:1px solid var(--line); border-radius:var(--radius-sm); margin-bottom:18px; }
        .avatar { width:40px;height:40px;border-radius:11px;background:var(--panel-hi);display:grid;place-items:center;
          font-weight:700;color:var(--teal);border:1px solid var(--line);font-size:14px; }
        nav { display:flex; flex-direction:column; gap:4px; }
        .side-item { display:flex; align-items:center; gap:12px; padding:11px 12px; border-radius:10px;
          text-align:left; color:var(--text-dim); transition:all 0.13s; position:relative; }
        .side-item:hover { background:var(--panel); }
        .side-item.on { background:var(--panel-hi); color:var(--text); }
        .side-item.on .si-icon { color:var(--teal); }
        .si-icon { font-size:16px; width:20px; text-align:center; }
        .si-label { font-weight:600; font-size:14px; }
        .si-hint { font-size:11px; color:var(--text-mute); }
        .si-badge { margin-left:auto; background:var(--crit); color:#fff; font-size:11px; font-weight:700;
          min-width:20px; height:20px; border-radius:10px; display:grid; place-items:center; padding:0 6px;
          animation:pulseCrit 1.4s infinite; }
        .side-foot { padding-top:14px; border-top:1px solid var(--line-soft); display:flex; flex-direction:column; gap:10px; }
        .hand-off { display:flex; align-items:center; justify-content:center; gap:8px; padding:10px 12px;
          border-radius:10px; font-size:13px; font-weight:600; color:var(--teal);
          background:var(--panel); border:1px solid var(--teal-dim); transition:all 0.13s; }
        .hand-off:hover { background:var(--panel-hi); box-shadow:0 0 0 3px var(--teal-glow); }
        .ws-main { padding:28px 34px; max-width:1180px; }
        @media (max-width:820px){ .ws{grid-template-columns:1fr;} .ws-side{position:static;height:auto;} }
      `}</style>
    </div>
  );
}
