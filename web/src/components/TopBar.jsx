import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useApp } from "../context/AppContext";

const FEATURE_LINKS = [
  ["/dashboard", "Dashboard"],
  ["/scribe", "Scribe"],
  ["/translate", "Translate"],
  ["/consent", "Consent"],
  ["/discharge", "Discharge"],
  ["/handoff", "Handoff"],
  ["/orientation", "Orientation"],
];

export default function TopBar() {
  const { staff, logout, patient } = useApp();
  const location = useLocation();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const s = await api.status();
        if (!cancelled) setStatus(s);
      } catch {
        if (!cancelled) setStatus(null);
      }
    }
    poll();
    const id = setInterval(poll, 10000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div id="topbar">
      <span className="brand">Doctor Offline</span>

      {staff && (
        <span className="nav-links">
          {FEATURE_LINKS.map(([path, label]) => (
            <Link key={path} to={path}>
              <button className={location.pathname === path ? "active" : ""}>{label}</button>
            </Link>
          ))}
        </span>
      )}

      <span
        className={`pill ${status ? (status.network_reachable ? "on" : "off") : ""}`}
        title={status ? `Ollama (${status.model}): ${status.ollama_reachable ? "reachable" : "unreachable"}` : ""}
      >
        {status ? (status.network_reachable ? "NETWORK: ON" : "NETWORK: OFF") : "NETWORK: ?"}
      </span>

      {staff && (
        <>
          <span className="muted">
            {staff.name}
            {patient ? ` — ${patient.name} · Room ${patient.room || "-"}` : ""}
          </span>
          <button onClick={() => navigate("/patients")}>Switch patient</button>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Log out
          </button>
        </>
      )}
    </div>
  );
}
