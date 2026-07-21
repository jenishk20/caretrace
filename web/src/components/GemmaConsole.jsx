import { useEffect, useRef, useState } from "react";
import { api } from "../api";

// Live on-device model console. A floating dock (bottom-right) that shows
// the most recent on-device model calls — prompt preview, JSON/text output, and
// how many milliseconds each took. It only polls while open, so it never adds
// background load during the demo.
const KIND_LABEL = { json: "JSON extract", chat: "Generate", vision: "Vision OCR" };
const KIND_COLOR = { json: "#2fe6c8", chat: "#5b8cff", vision: "#a78bfa" };

export default function GemmaConsole() {
  const [open, setOpen] = useState(false);
  const [model, setModel] = useState("");
  const [calls, setCalls] = useState([]);
  const lastId = useRef(0);

  useEffect(() => {
    if (!open) return;
    let alive = true;
    const tick = () =>
      api.gemmaLogs(20)
        .then((d) => { if (alive) { setModel(d.model); setCalls(d.calls || []); if (d.calls?.[0]) lastId.current = d.calls[0].id; } })
        .catch(() => {});
    tick();
    const iv = setInterval(tick, 2500);
    return () => { alive = false; clearInterval(iv); };
  }, [open]);

  const lastMs = calls[0]?.duration_ms;

  return (
    <>
      <button className="gc-fab" onClick={() => setOpen((v) => !v)} title="Live on-device model console">
        <span className="gc-dot" />
        ◈ gpt-oss {open ? "▾" : "▴"}
        {!open && lastMs != null && <span className="gc-fab-ms">{lastMs}ms</span>}
      </button>

      {open && (
        <div className="gc-panel">
          <div className="gc-head">
            <div>
              <b style={{ fontSize: 13 }}>On-device inference</b>
              <div className="muted" style={{ fontSize: 11 }}>{model || "gpt-oss:20b"} · via Ollama · nothing leaves the device</div>
            </div>
            <button className="gc-x" onClick={() => setOpen(false)}>✕</button>
          </div>
          <div className="gc-body">
            {calls.length === 0 && (
              <div className="muted" style={{ fontSize: 12, padding: "10px 2px" }}>
                No calls yet. Run an input or ask the room — each local model call appears here with its latency.
              </div>
            )}
            {calls.map((c) => (
              <div key={c.id} className="gc-call">
                <div className="row between" style={{ marginBottom: 4 }}>
                  <span className="gc-kind" style={{ color: KIND_COLOR[c.kind] || "#8a97bd" }}>
                    ● {KIND_LABEL[c.kind] || c.kind}
                  </span>
                  <span className="gc-ms">{c.duration_ms}ms</span>
                </div>
                <div className="gc-io">
                  <span className="gc-tag">in {c.prompt_chars}c</span>
                  <span className="gc-txt">{c.prompt_preview}</span>
                </div>
                <div className="gc-io">
                  <span className="gc-tag out">out {c.output_chars}c</span>
                  <span className="gc-txt gc-mono">{c.output_preview}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <style>{`
        .gc-fab { position: fixed; right: 18px; bottom: 18px; z-index: 80;
          display: flex; align-items: center; gap: 7px; padding: 8px 13px; border-radius: 999px;
          background: var(--panel); border: 1px solid var(--teal-dim); color: var(--text);
          font-size: 13px; font-weight: 600; box-shadow: var(--shadow-lg); cursor: pointer; }
        .gc-fab:hover { border-color: var(--teal); }
        .gc-fab-ms { font-size: 11px; color: var(--text-mute); font-weight: 500; }
        .gc-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--teal);
          box-shadow: 0 0 0 0 rgba(47,230,200,0.6); animation: gcPulse 1.8s infinite; }
        .gc-panel { position: fixed; right: 18px; bottom: 66px; z-index: 80;
          width: 380px; max-width: calc(100vw - 36px); max-height: 62vh;
          display: flex; flex-direction: column;
          background: var(--bg-soft); border: 1px solid var(--line); border-radius: 14px;
          box-shadow: var(--shadow-lg); overflow: hidden; }
        .gc-head { display: flex; justify-content: space-between; align-items: center;
          padding: 12px 14px; border-bottom: 1px solid var(--line); }
        .gc-x { background: none; border: none; color: var(--text-mute); cursor: pointer; font-size: 14px; }
        .gc-x:hover { color: var(--text); }
        .gc-body { overflow: auto; padding: 10px 12px; display: flex; flex-direction: column; gap: 10px; }
        .gc-call { border: 1px solid var(--line-soft); border-radius: 10px; padding: 10px 11px; background: var(--panel); }
        .gc-kind { font-size: 12px; font-weight: 700; }
        .gc-ms { font-size: 12px; font-weight: 700; color: var(--teal); }
        .gc-io { display: flex; gap: 7px; margin-top: 5px; }
        .gc-tag { flex: none; font-size: 10px; padding: 1px 6px; border-radius: 5px; height: fit-content;
          background: var(--panel-2); border: 1px solid var(--line); color: var(--text-mute); }
        .gc-tag.out { color: var(--teal); border-color: var(--teal-dim); }
        .gc-txt { font-size: 11.5px; color: var(--text-dim); line-height: 1.45;
          max-height: 54px; overflow: hidden; word-break: break-word; }
        .gc-mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--text); }
        @keyframes gcPulse { 0% { box-shadow: 0 0 0 0 rgba(47,230,200,0.55); }
          70% { box-shadow: 0 0 0 7px rgba(47,230,200,0); } 100% { box-shadow: 0 0 0 0 rgba(47,230,200,0); } }
      `}</style>
    </>
  );
}
