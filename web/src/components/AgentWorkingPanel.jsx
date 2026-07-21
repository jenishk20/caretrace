const LAYERS = {
  extract_note_and_facts: "model",
  suggest_billing_codes: "model",
  draft_handoff: "model",
  draft_patient_summary: "model",
  reconcile_medication: "deterministic",
  run_guardian: "deterministic",
  sweep_forgotten_orders: "deterministic",
  ingest_facts: "record",
};

const ROUTES = {
  speech: ["extract_note_and_facts", "ingest_facts", "run_guardian", "suggest_billing_codes", "draft_handoff", "draft_patient_summary"],
  image: ["extract_note_and_facts", "reconcile_medication", "ingest_facts", "run_guardian"],
  text: ["extract_note_and_facts", "ingest_facts"],
};

const LABELS = {
  extract_note_and_facts: "Extract note + facts",
  ingest_facts: "Update patient graph",
  run_guardian: "Run Guardian rules",
  reconcile_medication: "Reconcile medication",
  suggest_billing_codes: "Suggest billing codes",
  draft_handoff: "Draft SBAR handoff",
  draft_patient_summary: "Draft patient summary",
  sweep_forgotten_orders: "Sweep forgotten orders",
};

export { LAYERS, LABELS };

export default function AgentWorkingPanel({ busy, inputKind, trace = [] }) {
  const completed = new Map(trace.map((event) => [event.tool, event.status]));
  const tools = trace.length ? trace.map((event) => event.tool) : (busy ? [] : ROUTES[inputKind] || ROUTES.text);
  return (
    <section className="card agent-working" aria-live="polite">
      <div className="row between">
        <div>
          <div className="eyebrow">Agent orchestration</div>
          <h3>{busy ? (trace.length ? "Working locally…" : "Starting local run…") : trace.length ? "Run trace" : "Route preview"}</h3>
        </div>
        <span className={`agent-state ${busy ? "running" : ""}`}>{busy ? "RUNNING" : "NETWORK OFF"}</span>
      </div>
      <div className="tool-lane">
        {tools.map((tool, index) => {
          const layer = LAYERS[tool] || "record";
          const status = completed.get(tool);
          return (
            <div className={`tool-chip ${layer} ${busy && !status ? "pending" : ""} ${status || ""}`} key={`${tool}-${index}`}>
              <span className="tool-dot" />
              <span>{LABELS[tool] || tool}</span>
              <small>{layer}</small>
            </div>
          );
        })}
        {busy && tools.length === 0 && <span className="muted" style={{ fontSize: 12 }}>Waiting for the first recorded tool call…</span>}
      </div>
      <div className="layer-key">
        <span className="model">● model language</span>
        <span className="deterministic">● deterministic rules</span>
        <span className="record">● local record</span>
      </div>
      <style>{`
        .agent-working{padding:20px;border-color:var(--teal-dim);overflow:hidden;position:relative}
        .eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--teal);font-weight:800}
        .agent-working h3{font-size:18px;margin-top:3px}.agent-state{font:700 10px var(--mono);letter-spacing:.1em;color:var(--ok)}
        .agent-state.running{color:var(--teal);animation:pulseWarn 1.4s infinite}.tool-lane{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}
        .tool-chip{display:grid;grid-template-columns:8px auto;column-gap:8px;align-items:center;padding:9px 11px;border:1px solid var(--line);border-radius:10px;background:var(--bg-soft);font-size:12px}
        .tool-chip small{grid-column:2;font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-mute)}
        .tool-dot{width:7px;height:7px;border-radius:50%;background:currentColor}.tool-chip.model{color:var(--violet)}
        .tool-chip.deterministic{color:var(--warn)}.tool-chip.record{color:var(--teal)}.tool-chip.pending{opacity:.42;animation:pulseWarn 1.6s infinite}
        .tool-chip.ok{border-color:currentColor;background:color-mix(in srgb,currentColor 8%,var(--bg-soft))}.tool-chip.error{color:var(--crit);border-color:var(--crit)}
        .layer-key{display:flex;gap:14px;flex-wrap:wrap;margin-top:14px;font-size:10px;color:var(--text-mute)}
        .layer-key .model{color:var(--violet)}.layer-key .deterministic{color:var(--warn)}.layer-key .record{color:var(--teal)}
      `}</style>
    </section>
  );
}
