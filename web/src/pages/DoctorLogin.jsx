import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { session } from "../lib/session.js";
import AuthShell from "../components/AuthShell.jsx";

export default function DoctorLogin() {
  const nav = useNavigate();
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("doctor");
  const [password, setPassword] = useState("confide");
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      let s;
      if (mode === "register") {
        await api.staffRegister(username, password, name || username);
        s = await api.staffLogin(username, password);
      } else {
        s = await api.staffLogin(username, password);
      }
      session.setStaff(s);
      nav("/doctor");
    } catch (e2) {
      setErr(e2.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell icon="🩺" title="Healthcare practitioner sign-in" subtitle="Round, capture, and watch the Guardian work.">
      <form onSubmit={submit}>
        {mode === "register" && (
          <label className="field">
            <span>Full name</span>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Dr. Alex Reyes" />
          </label>
        )}
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
          {busy ? <span className="spinner" /> : mode === "register" ? "Create account" : "Sign in"}
        </button>
      </form>
      <div className="row between" style={{ marginTop: 16, fontSize: 13 }}>
        <button className="btn-ghost" style={{ background: "none", border: "none", color: "var(--teal)" }}
          onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "Create a healthcare practitioner account" : "Have an account? Sign in"}
        </button>
        <Link to="/" className="muted">← Home</Link>
      </div>
      <style>{`.err{background:rgba(255,90,110,0.1);border:1px solid rgba(255,90,110,0.4);color:var(--crit);
        padding:10px 12px;border-radius:10px;font-size:13px;margin-bottom:12px;}`}</style>
    </AuthShell>
  );
}
