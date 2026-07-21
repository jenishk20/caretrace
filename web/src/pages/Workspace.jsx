import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { session } from "../lib/session.js";
import NetworkPill from "../components/NetworkPill.jsx";
import LocalModelConsole from "../components/LocalModelConsole.jsx";
import VisitFlow from "../views/VisitFlow.jsx";
import Overview from "../views/Overview.jsx";
import ScribeView from "../views/ScribeView.jsx";
import VisitsView from "../views/VisitsView.jsx";
import ConsentView from "../views/ConsentView.jsx";
import DischargeView from "../views/DischargeView.jsx";
import HandoffView from "../views/HandoffView.jsx";
import PrescriptionStep from "../views/PrescriptionStep.jsx";
import RoiView from "../views/RoiView.jsx";

const NAV = [
  { key: "visit", label: "Guided visit", icon: "🧭", hint: "Onboard → discharge" },
  { key: "dashboard", label: "Dashboard", icon: "🗂", hint: "Everything, one place" },
  { key: "roi", label: "ROI & proof", icon: "↗", hint: "Time, coding, safety" },
  { key: "overview", label: "Overview", icon: "◈", hint: "Graph & Guardian" },
  { key: "scribe", label: "Scribe", icon: "🎧", hint: "Capture a round" },
  { key: "consent", label: "Consent", icon: "📋", hint: "Explain a form" },
  { key: "prescription", label: "Prescription", icon: "℞", hint: "Scan a medicine" },
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
  const activeNav = NAV.find((item) => item.key === tab) || NAV[0];

  if (!patient) return <div style={{ display: "grid", placeItems: "center", height: "100vh" }}><span className="spinner" /></div>;

  const shared = { patient, pid, staff, snapshot, refresh, setTab };

  return (
    <div className="ws">
      <aside className="ws-side">
        <div className="row" style={{ gap: 10, padding: "4px 8px 20px" }}>
          <span style={{ color: "var(--teal)", fontSize: 20 }}>◈</span>
          <b>CareTrace</b>
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
          <NetworkPill />
        </div>
      </aside>

      <main className="ws-main">
        <header className="ws-utility">
          <div>
            <div className="ws-kicker">CARETRACE CLINICAL WORKSPACE</div>
            <h1>{activeNav.label}</h1>
            <p>{activeNav.hint} · all facts remain on this device.</p>
          </div>
          <div className="ws-state">
            <div className="ws-state-item"><span>ACTIVE FACTS</span><b>{snapshot.nodes?.length || 0}</b></div>
            <div className={`ws-state-item ${activeAlerts.length ? "alert" : ""}`}><span>GUARDIAN</span><b>{activeAlerts.length ? `${activeAlerts.length} review` : "clear"}</b></div>
          </div>
        </header>
        {tab === "visit" && <VisitFlow {...shared} />}
        {tab === "dashboard" && <VisitsView {...shared} />}
        {tab === "roi" && <RoiView {...shared} />}
        {tab === "overview" && <Overview {...shared} />}
        {tab === "scribe" && <ScribeView {...shared} />}
        {tab === "consent" && <ConsentView {...shared} />}
        {tab === "prescription" && <PrescriptionStep {...shared} />}
        {tab === "discharge" && <DischargeView {...shared} />}
        {tab === "handoff" && <HandoffView {...shared} />}
      </main>

      <LocalModelConsole />

      <style>{`
        .ws { display:grid; grid-template-columns:272px 1fr; min-height:100vh; }
        .ws-side { border-right:1px solid var(--line); padding:22px 16px; display:flex; flex-direction:column;
          position:sticky; top:0; height:100vh; background:linear-gradient(180deg,rgba(9,29,40,0.96),rgba(5,18,27,0.92)); }
        .side-back { text-align:left; color:var(--text-mute); font-size:13px; padding:6px 8px; margin-bottom:14px; }
        .side-back:hover { color:var(--teal); }
        .side-pt { display:flex; gap:12px; align-items:center; padding:14px; background:linear-gradient(140deg,rgba(26,64,80,0.9),rgba(13,36,48,0.9));
          border:1px solid var(--line); border-radius:var(--radius-sm); margin-bottom:18px; }
        .avatar { width:42px;height:42px;border-radius:13px;background:linear-gradient(145deg,var(--panel-hi),var(--bg-soft));display:grid;place-items:center;
          font-weight:700;color:var(--teal);border:1px solid var(--line);font-size:14px; }
        nav { display:flex; flex-direction:column; gap:4px; }
        .side-item { display:flex; align-items:center; gap:12px; padding:11px 12px; border-radius:10px;
          text-align:left; color:var(--text-dim); transition:all 0.13s; position:relative; }
        .side-item:hover { background:var(--panel); }
        .side-item.on { background:linear-gradient(90deg,rgba(100,232,210,0.13),rgba(100,232,210,0.03)); color:var(--text); border:1px solid rgba(100,232,210,0.16); }
        .side-item.on .si-icon { color:var(--teal); }
        .si-icon { font-size:16px; width:20px; text-align:center; }
        .si-label { font-weight:600; font-size:14px; }
        .si-hint { font-size:11px; color:var(--text-mute); }
        .si-badge { margin-left:auto; background:var(--crit); color:#fff; font-size:11px; font-weight:700;
          min-width:20px; height:20px; border-radius:10px; display:grid; place-items:center; padding:0 6px;
          animation:pulseCrit 1.4s infinite; }
        .side-foot { padding-top:14px; border-top:1px solid var(--line-soft); }
        .ws-main { width:min(100%,1240px); padding:34px 42px 60px; }
        .ws-utility { display:flex; justify-content:space-between; align-items:end; gap:20px; margin-bottom:30px; padding:22px 24px; border:1px solid var(--line); border-radius:var(--radius); background:linear-gradient(120deg,rgba(29,78,91,0.58),rgba(12,35,47,0.58)); box-shadow:var(--shadow); }
        .ws-kicker { color:var(--teal); font-size:11px; letter-spacing:0.14em; font-weight:800; }
        .ws-utility h1 { margin:4px 0 2px; font-size:28px; letter-spacing:-0.035em; }
        .ws-utility p { color:var(--text-mute); font-size:13px; }
        .ws-state { display:flex; gap:8px; flex-wrap:wrap; }
        .ws-state-item { min-width:92px; padding:9px 11px; border:1px solid var(--line); border-radius:10px; background:rgba(5,19,28,0.42); }
        .ws-state-item span { display:block; color:var(--text-mute); font-size:9px; letter-spacing:0.09em; font-weight:800; }
        .ws-state-item b { display:block; margin-top:2px; color:var(--teal); font-size:13px; }
        .ws-state-item.alert b { color:var(--warn); }
        @media (max-width:820px){ .ws{grid-template-columns:1fr;} .ws-side{position:static;height:auto;} .ws-main{padding:22px 18px 48px;} .ws-utility{align-items:flex-start;flex-direction:column;} }
      `}</style>
    </div>
  );
}
