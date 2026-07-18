import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { session } from "../lib/session.js";
import NetworkPill from "../components/NetworkPill.jsx";

export default function Roster() {
  const nav = useNavigate();
  const staff = session.staff();
  const [patients, setPatients] = useState([]);
  const [showAdmit, setShowAdmit] = useState(false);

  const load = () => api.listPatients().then(setPatients).catch(() => {});
  useEffect(() => { load(); }, []);

  function logout() {
    session.clearStaff();
    nav("/");
  }

  return (
    <div style={{ minHeight: "100%" }}>
      <div className="topbar">
        <div className="row" style={{ gap: 10 }}>
          <span style={{ color: "var(--teal)", fontSize: 20 }}>◈</span>
          <b>Confide</b>
          <span className="muted" style={{ fontSize: 13 }}>· Care roster</span>
        </div>
        <div className="row" style={{ gap: 14 }}>
          <NetworkPill />
          <span className="pill">🩺 {staff?.name}</span>
          <button className="btn btn-ghost" style={{ padding: "7px 12px" }} onClick={logout}>Log out</button>
        </div>
      </div>

      <div style={{ maxWidth: 980, margin: "0 auto", padding: 32 }}>
        <div className="row between" style={{ marginBottom: 20 }}>
          <div>
            <h1 style={{ fontSize: 26, letterSpacing: "-0.02em" }}>Patients</h1>
            <p className="muted">Pick a patient to open their living record.</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowAdmit(true)}>+ Admit patient</button>
        </div>

        <div className="grid">
          {patients.map((p) => (
            <button key={p.id} className="pt-card" onClick={() => nav(`/doctor/patient/${p.id}`)}>
              <div className="row between">
                <div className="avatar">{p.name.split(" ").map((w) => w[0]).slice(0, 2).join("")}</div>
                <span className={`tag ${p.status}`} style={{
                  background: p.status === "admitted" ? "rgba(62,224,138,0.12)" : "var(--panel-2)",
                  color: p.status === "admitted" ? "var(--ok)" : "var(--text-mute)",
                }}>{p.status}</span>
              </div>
              <div className="pt-name">{p.name}</div>
              <div className="muted" style={{ fontSize: 13 }}>
                {p.age ? `${p.age} yrs · ` : ""}Room {p.room || "—"} · {p.mrn || "no MRN"}
              </div>
              {p.reason_for_visit && <div className="pt-reason">{p.reason_for_visit}</div>}
            </button>
          ))}
          {patients.length === 0 && <div className="muted">No patients yet — admit one to begin.</div>}
        </div>
      </div>

      {showAdmit && <AdmitModal staff={staff} onClose={() => setShowAdmit(false)} onDone={(p) => { setShowAdmit(false); load(); nav(`/doctor/patient/${p.id}`); }} />}

      <style>{`
        .topbar { display:flex; justify-content:space-between; align-items:center; padding:16px 28px;
          border-bottom:1px solid var(--line); background:rgba(10,14,26,0.7); backdrop-filter:blur(10px);
          position:sticky; top:0; z-index:10; }
        .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:16px; }
        .pt-card { text-align:left; padding:20px; background:linear-gradient(180deg,var(--panel),var(--bg-soft));
          border:1px solid var(--line); border-radius:var(--radius); transition:all 0.16s; }
        .pt-card:hover { border-color:var(--teal-dim); transform:translateY(-2px); box-shadow:var(--shadow-lg); }
        .avatar { width:42px;height:42px;border-radius:12px;background:var(--panel-hi);display:grid;place-items:center;
          font-weight:700;color:var(--teal); border:1px solid var(--line); }
        .pt-name { font-size:18px; font-weight:700; margin:14px 0 2px; }
        .pt-reason { margin-top:12px; font-size:13px; color:var(--text-dim); background:var(--bg-soft);
          padding:8px 12px; border-radius:8px; border:1px solid var(--line-soft); }
      `}</style>
    </div>
  );
}

function AdmitModal({ staff, onClose, onDone }) {
  const [f, setF] = useState({
    name: "", age: "", room: "", mrn: "", reason_for_visit: "",
    primary_language: "en",
    username: "", password: "confide", allergies: "", medications: "",
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const p = await api.createPatient({
        name: f.name,
        staff_id: staff.staff_id,
        age: f.age ? Number(f.age) : null,
        room: f.room || null,
        mrn: f.mrn || null,
        reason_for_visit: f.reason_for_visit || null,
        primary_language: f.primary_language || "en",
        username: f.username || null,
        password: f.password || null,
        known_allergies: f.allergies ? f.allergies.split(",").map((s) => s.trim()).filter(Boolean) : [],
        current_medications: f.medications ? f.medications.split(",").map((s) => s.trim()).filter(Boolean) : [],
      });
      onDone(p);
    } catch (e2) {
      setErr(e2.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="card modal fade-up" onClick={(e) => e.stopPropagation()}>
        <h2 style={{ fontSize: 22, marginBottom: 4 }}>Admit patient</h2>
        <p className="muted" style={{ marginBottom: 20, fontSize: 14 }}>
          Facts you enter here become the first nodes of their living record — and the Guardian checks them immediately.
        </p>
        <form onSubmit={submit}>
          <div className="two">
            <label className="field"><span>Full name</span><input className="input" required value={f.name} onChange={set("name")} placeholder="María González" /></label>
            <label className="field"><span>Age</span><input className="input" value={f.age} onChange={set("age")} placeholder="68" /></label>
          </div>
          <div className="two">
            <label className="field"><span>Room</span><input className="input" value={f.room} onChange={set("room")} placeholder="4B" /></label>
            <label className="field"><span>MRN</span><input className="input" value={f.mrn} onChange={set("mrn")} placeholder="MRN-04821" /></label>
          </div>
          <div className="two">
            <label className="field"><span>Reason for visit</span><input className="input" value={f.reason_for_visit} onChange={set("reason_for_visit")} placeholder="Chest pain" /></label>
            <label className="field"><span>Preferred language</span>
              <select className="input" value={f.primary_language} onChange={set("primary_language")}>
                <option value="en">English</option>
                <option value="es">Spanish (Español)</option>
                <option value="zh">Chinese (中文)</option>
                <option value="vi">Vietnamese (Tiếng Việt)</option>
                <option value="ar">Arabic (العربية)</option>
                <option value="fr">French (Français)</option>
                <option value="ru">Russian (Русский)</option>
                <option value="ko">Korean (한국어)</option>
                <option value="hi">Hindi (हिन्दी)</option>
                <option value="pt">Portuguese (Português)</option>
                <option value="tl">Tagalog</option>
              </select>
            </label>
          </div>
          <label className="field"><span>Known allergies (comma-separated)</span><input className="input" value={f.allergies} onChange={set("allergies")} placeholder="Penicillin" /></label>
          <label className="field"><span>Current medications (comma-separated)</span><input className="input" value={f.medications} onChange={set("medications")} placeholder="Warfarin" /></label>
          <div className="sep" />
          <div className="muted" style={{ fontSize: 12, marginBottom: 10 }}>PATIENT LOGIN (they'll use this to talk to Confide)</div>
          <div className="two">
            <label className="field"><span>Username</span><input className="input" value={f.username} onChange={set("username")} placeholder="maria" /></label>
            <label className="field"><span>Password</span><input className="input" value={f.password} onChange={set("password")} /></label>
          </div>
          {err && <div style={{ color: "var(--crit)", fontSize: 13, marginBottom: 10 }}>{err}</div>}
          <div className="row between" style={{ marginTop: 8 }}>
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button className="btn btn-primary" disabled={busy}>{busy ? <span className="spinner" /> : "Admit & open record"}</button>
          </div>
        </form>
      </div>
      <style>{`
        .overlay { position:fixed; inset:0; background:rgba(4,7,14,0.7); backdrop-filter:blur(4px);
          display:grid; place-items:center; z-index:50; padding:24px; }
        .modal { width:560px; max-width:100%; padding:28px; max-height:90vh; overflow:auto; }
        .two { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
      `}</style>
    </div>
  );
}
