import { useEffect, useRef, useState } from "react";
import { api } from "../api";

// Live local-model console. A floating dock (bottom-right) that shows
// the most recent on-device model calls — prompt preview, JSON/text output, and
// how many milliseconds each took. It only polls while open, so it never adds
// background load during the demo.
const KIND_LABEL = { json: "JSON extract", chat: "Generate", vision: "Vision OCR" };
const KIND_COLOR = { json: "#2fe6c8", chat: "#5b8cff", vision: "#a78bfa" };

const fmtMb = (mb) => (mb == null ? "—" : mb >= 1000 ? `${(mb / 1000).toFixed(1)} GB` : `${mb} MB`);
const fmtTok = (n) => (n == null ? "0" : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`);

export default function LocalModelConsole() {
  const [open, setOpen] = useState(false);
  const [model, setModel] = useState("");
  const [calls, setCalls] = useState([]);
  const [session, setSession] = useState(null);
  const [resident, setResident] = useState(null);
  const lastId = useRef(0);

  useEffect(() => {
    if (!open) return;
    let alive = true;
    const tick = () =>
      api.modelLogs(20)
        .then((d) => {
          if (!alive) return;
          setModel(d.model);
          setCalls(d.calls || []);
          setSession(d.session || null);
          setResident(d.resident || null);
          if (d.calls?.[0]) lastId.current = d.calls[0].id;
        })
        .catch(() => {});
    tick();
    const iv = setInterval(tick, 2500);
    return () => { alive = false; clearInterval(iv); };
  }, [open]);

  const lastMs = calls[0]?.duration_ms;
  const lastTps = calls[0]?.tokens_per_sec;

  return (
    <>
      <button className="gc-fab" onClick={() => setOpen((v) => !v)} title="Live GPT-OSS inference console">
        <span className="gc-dot" />
        ◈ GPT-OSS {open ? "▾" : "▴"}
        {!open && lastMs != null && (
          <span className="gc-fab-ms">{lastTps != null ? `${lastTps} tok/s` : `${lastMs}ms`}</span>
        )}
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
          {(resident || session) && (
            <div className="gc-stats">
              {resident && (
                <span className="gc-stat gc-stat-live" title="Model resident in memory (ollama ps)">
                  <span className="gc-dot" style={{ width: 6, height: 6 }} />
                  resident · {fmtMb(resident.vram_mb ?? resident.size_mb)}
                  {resident.gpu_pct != null && ` · ${resident.gpu_pct}% GPU`}
                </span>
              )}
              {session && (
                <span className="gc-stat" title="Total tokens processed this session (in + out)">
                  {fmtTok(session.tokens_total)} tok · {session.calls} calls
                </span>
              )}
            </div>
          )}
          <div className="gc-body">
            {calls.length === 0 && (
              <div className="muted" style={{ fontSize: 12, padding: "10px 2px" }}>
                No calls yet. Capture a round or ask the room — each GPT-OSS call appears here with its latency.
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
                {(c.tokens_per_sec != null || c.tokens_out != null || c.tokens_in != null) && (
                  <div className="gc-metrics">
                    {c.tokens_per_sec != null && <span className="gc-metric">⚡ {c.tokens_per_sec} tok/s</span>}
                    {(c.tokens_in != null || c.tokens_out != null) && (
                      <span className="gc-metric">{c.tokens_in ?? "?"} in / {c.tokens_out ?? "?"} out</span>
                    )}
                    {c.prompt_ms != null && <span className="gc-metric gc-metric-dim">prefill {c.prompt_ms}ms</span>}
                    {c.eval_ms != null && <span className="gc-metric gc-metric-dim">gen {c.eval_ms}ms</span>}
                    {c.load_ms ? <span className="gc-metric gc-metric-dim">load {c.load_ms}ms</span> : null}
                  </div>
                )}
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
        .gc-metrics { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 5px; }
        .gc-metric { font-size: 10px; padding: 1px 6px; border-radius: 5px;
          background: rgba(47,230,200,0.09); border: 1px solid var(--teal-dim); color: var(--teal); }
        .gc-metric-dim { background: var(--panel-2); border-color: var(--line); color: var(--text-mute); }
        .gc-stats { display: flex; flex-wrap: wrap; gap: 8px; padding: 8px 14px;
          border-bottom: 1px solid var(--line); background: var(--panel); }
        .gc-stat { font-size: 11px; padding: 3px 9px; border-radius: 999px;
          background: var(--panel-2); border: 1px solid var(--line); color: var(--text-dim);
          display: inline-flex; align-items: center; gap: 6px; }
        .gc-stat-live { border-color: var(--teal-dim); color: var(--teal); }
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
