import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { session } from "../lib/session.js";
import AuthShell from "../components/AuthShell.jsx";

export default function PatientLogin() {
  const nav = useNavigate();
  const [username, setUsername] = useState("maria");
  const [password, setPassword] = useState("confide");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const p = await api.patientLogin(username, password);
      session.setPatient(p);
      nav("/patient");
    } catch (e2) {
      setErr(e2.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell icon="💙" title="Welcome" subtitle="Confide is here for you — ask anything about your care.">
      <form onSubmit={submit}>
        <label className="field">
          <span>Username</span>
          <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label className="field">
          <span>Password</span>
          <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {err && <div className="err">{err}</div>}
        <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center", marginTop: 6 }} disabled={busy}>
          {busy ? <span className="spinner" /> : "Sign in"}
        </button>
      </form>
      <div className="row between" style={{ marginTop: 16, fontSize: 13 }}>
        <span className="muted">Your care team set this up for you.</span>
        <Link to="/" className="muted">← Home</Link>
      </div>
      <style>{`.err{background:rgba(255,90,110,0.1);border:1px solid rgba(255,90,110,0.4);color:var(--crit);
        padding:10px 12px;border-radius:10px;font-size:13px;margin-bottom:12px;}`}</style>
    </AuthShell>
  );
}
