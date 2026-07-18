import { useEffect, useState } from "react";
import { api } from "../api";

// The literal proof-of-offline indicator. Turn Wi-Fi off and it flips to
// "NETWORK OFF" while everything keeps working — Gemma still reachable locally.
export default function NetworkPill() {
  const [st, setSt] = useState(null);

  useEffect(() => {
    let alive = true;
    const tick = () => api.status().then((s) => alive && setSt(s)).catch(() => {});
    tick();
    const id = setInterval(tick, 4000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  if (!st) return null;
  const off = !st.network_reachable;
  return (
    <div className="row" style={{ gap: 8 }}>
      <span
        className="pill"
        title="Best-effort probe of an external host"
        style={{
          borderColor: off ? "var(--teal-dim)" : "var(--line)",
          color: off ? "var(--teal)" : "var(--text-mute)",
          background: off ? "rgba(47,230,200,0.08)" : "var(--panel-2)",
        }}
      >
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: off ? "var(--teal)" : "var(--text-mute)",
          }}
        />
        NETWORK {off ? "OFF" : "ON"}
      </span>
      <span
        className="pill"
        title="Local model via Ollama"
        style={{
          borderColor: st.ollama_reachable ? "var(--line)" : "var(--crit)",
          color: st.ollama_reachable ? "var(--text-dim)" : "var(--crit)",
        }}
      >
        {st.ollama_reachable ? "◈" : "○"} {st.model}
      </span>
    </div>
  );
}
