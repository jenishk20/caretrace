const SEVERITY = {
  critical: { color: "var(--crit)", glow: "var(--crit-glow)", label: "Critical", icon: "⛔" },
  warning: { color: "var(--warn)", glow: "var(--warn-glow)", label: "Watch", icon: "⚠" },
  info: { color: "var(--teal)", glow: "var(--teal-glow)", label: "Note", icon: "◈" },
};

const TYPE_LABEL = {
  allergy: "Allergy conflict",
  interaction: "Drug interaction",
  contradiction: "Record contradiction",
  forgotten_order: "Forgotten order",
  self_check: "Self-check",
};

export default function GuardianAlert({ alert, onAck, onDismiss, live = false }) {
  const s = SEVERITY[alert.severity] || SEVERITY.info;
  return (
    <div
      className="card"
      style={{
        padding: 16,
        borderColor: s.color,
        borderLeft: `3px solid ${s.color}`,
        animation: live ? `slideIn 0.4s ease both, ${alert.severity === "critical" ? "pulseCrit" : "pulseWarn"} 1.6s ease-in-out 3` : "fadeUp 0.3s ease both",
      }}
    >
      <div className="row between" style={{ marginBottom: 8 }}>
        <div className="row" style={{ gap: 8 }}>
          <span style={{ fontSize: 16 }}>{s.icon}</span>
          <span className="tag" style={{ background: s.glow, color: s.color }}>
            {TYPE_LABEL[alert.atype] || alert.atype}
          </span>
        </div>
        <span className="row" style={{ gap: 6, fontSize: 11, color: "var(--text-mute)" }}>
          <span style={{ color: "var(--teal)" }}>◈ CareTrace</span>
          {live && <span style={{ color: s.color, fontWeight: 700 }}>· unprompted</span>}
        </span>
      </div>
      <div style={{ fontWeight: 700, marginBottom: 4 }}>{alert.title}</div>
      <div className="dim" style={{ fontSize: 14, lineHeight: 1.55 }}>{alert.message}</div>
      {(onAck || onDismiss) && alert.status === "active" && (
        <div className="row" style={{ gap: 8, marginTop: 12 }}>
          {onAck && (
            <button className="btn btn-ghost" style={{ padding: "7px 12px", fontSize: 13 }} onClick={() => onAck(alert)}>
              Acknowledge
            </button>
          )}
          {onDismiss && (
            <button className="btn btn-ghost" style={{ padding: "7px 12px", fontSize: 13 }} onClick={() => onDismiss(alert)}>
              Dismiss
            </button>
          )}
        </div>
      )}
      {alert.status !== "active" && (
        <div style={{ marginTop: 8 }}>
          <span className="pill" style={{ fontSize: 11 }}>{alert.status}</span>
        </div>
      )}
    </div>
  );
}
