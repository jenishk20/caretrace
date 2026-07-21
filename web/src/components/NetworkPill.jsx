import { useEffect, useState } from "react";
import { api } from "../api";

// Confide's runtime network mode. The backend never probes an external host;
// local Ollama remains reachable while external runtime networking is disabled.
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
        title="External runtime networking is disabled; no external host is probed"
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
