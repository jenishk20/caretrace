import NetworkPill from "./NetworkPill.jsx";

export default function AuthShell({ icon, title, subtitle, children }) {
  return (
    <div style={{ minHeight: "100%", display: "flex", flexDirection: "column" }}>
      <div className="row between" style={{ padding: "22px 32px" }}>
        <div className="row" style={{ gap: 10 }}>
          <span style={{ color: "var(--teal)", fontSize: 22 }}>◈</span>
          <b style={{ fontSize: 18 }}>CareTrace</b>
        </div>
        <NetworkPill />
      </div>
      <div style={{ flex: 1, display: "grid", placeItems: "center", padding: 24 }}>
        <div className="card fade-up" style={{ width: 400, maxWidth: "100%", padding: 32 }}>
          <div style={{ fontSize: 34, marginBottom: 12 }}>{icon}</div>
          <h2 style={{ fontSize: 24, letterSpacing: "-0.02em", marginBottom: 6 }}>{title}</h2>
          <p className="muted" style={{ marginBottom: 24, fontSize: 14 }}>{subtitle}</p>
          {children}
        </div>
      </div>
    </div>
  );
}
