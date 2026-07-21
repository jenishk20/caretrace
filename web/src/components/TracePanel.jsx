import { LABELS, LAYERS } from "./AgentWorkingPanel.jsx";

export default function TracePanel({ trace = [] }) {
  return (
    <div className="trace-stack">
      <details className="card trace-panel">
        <summary>Why did it do that? <span>{trace.length} tool calls</span></summary>
        <div className="trace-events">
          {trace.map((event, index) => (
            <div className="trace-event" key={`${event.tool}-${index}`}>
              <span className={`trace-num ${LAYERS[event.tool] || "record"}`}>{index + 1}</span>
              <div>
                <b>{LABELS[event.tool] || event.tool}</b>
                <div className="muted">{LAYERS[event.tool] || "record"} layer · {event.status}</div>
                {Object.keys(event.args || {}).length > 0 && <code>args {JSON.stringify(event.args)}</code>}
                <pre>{JSON.stringify(event.result_summary || {}, null, 2)}</pre>
              </div>
            </div>
          ))}
        </div>
      </details>
      <style>{`
        .trace-stack{display:grid;gap:14px}.trace-panel{padding:0}.trace-panel summary{cursor:pointer;padding:16px 18px;font-weight:700}
        .trace-panel summary span{float:right;color:var(--text-mute);font-size:12px}.trace-events{padding:0 18px 18px;display:grid;gap:12px}
        .trace-event{display:grid;grid-template-columns:28px 1fr;gap:10px}.trace-num{width:24px;height:24px;border-radius:8px;display:grid;place-items:center;background:var(--panel-hi);font-size:11px;font-weight:800}
        .trace-num.model{color:var(--violet)}.trace-num.deterministic{color:var(--warn)}.trace-num.record{color:var(--teal)}
        .trace-event .muted{font-size:10px;text-transform:uppercase;letter-spacing:.07em}.trace-event code{display:block;margin-top:5px;color:var(--text-dim);font-size:10px}
        .trace-event pre{white-space:pre-wrap;margin-top:5px;padding:8px;background:var(--bg);border-radius:7px;color:var(--text-dim);font:10px/1.4 var(--mono);max-height:130px;overflow:auto}
      `}</style>
    </div>
  );
}
