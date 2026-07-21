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

export default function AgentWorkingPanel({ busy, trace = [] }) {
  const completed = trace.filter((event) => event.status === "ok").length;
  const failed = trace.filter((event) => event.status === "error").length;
  const state = busy ? "RUNNING" : trace.length ? "DRAFT READY" : "READY";
  const title = busy ? (trace.length ? "Reviewing the record…" : "Preparing local workflow…") : trace.length ? "Workflow complete" : "Ready when you are";
  const description = busy
    ? "Only completed local steps appear here. You can review every draft before it is committed."
    : trace.length
      ? `${completed} local step${completed === 1 ? "" : "s"} completed${failed ? ` · ${failed} needs attention` : ""}.`
      : "Capture one bedside input. MedSignal will structure it, run safety checks, and prepare reviewable drafts.";

  return (
    <section className="card agent-working" aria-live="polite">
      <div className="row between">
        <div>
          <div className="eyebrow">Local workflow</div>
          <h3>{title}</h3>
        </div>
        <span className={`agent-state ${busy ? "running" : ""}`}>{state}</span>
      </div>
      <p className="workflow-description">{description}</p>
      {trace.length === 0 ? (
        <div className="workflow-phases" aria-label="Workflow phases">
          <div><span className="phase-icon model">1</span><b>Understand</b><small>Structure the bedside input.</small></div>
          <div><span className="phase-icon deterministic">2</span><b>Check safety</b><small>Run deterministic clinical checks.</small></div>
          <div><span className="phase-icon record">3</span><b>Prepare drafts</b><small>You decide what to approve.</small></div>
        </div>
      ) : (
        <ol className="workflow-progress">
          {trace.map((event, index) => {
            const layer = LAYERS[event.tool] || "record";
            const status = event.status || "working";
            return <li key={`${event.tool}-${index}`} className={`${layer} ${status}`}>
              <span className="progress-dot">{status === "ok" ? "✓" : status === "error" ? "!" : index + 1}</span>
              <div><b>{LABELS[event.tool] || event.tool}</b><small>{layer === "model" ? "local model" : layer === "deterministic" ? "safety rules" : "patient record"}</small></div>
              <span className="progress-status">{status === "ok" ? "Complete" : status === "error" ? "Needs review" : "Working"}</span>
            </li>;
          })}
          {busy && <li className="workflow-next"><span className="spinner" /><span>Preparing the next appropriate step…</span></li>}
        </ol>
      )}
      <div className="workflow-foot"><span>● on-device only</span><span>Clinician approval required for drafts</span></div>
      <style>{`
        .agent-working{padding:20px;border-color:var(--teal-dim);overflow:hidden;position:relative}
        .eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--teal);font-weight:800}
        .agent-working h3{font-size:18px;margin-top:3px}.agent-state{font:700 10px var(--mono);letter-spacing:.1em;color:var(--ok);padding:6px 8px;border-radius:999px;background:rgba(62,224,138,.1)}
        .agent-state.running{color:var(--teal);background:rgba(100,232,210,.1);animation:pulseWarn 1.4s infinite}.workflow-description{margin:12px 0 16px;color:var(--text-dim);font-size:13px;line-height:1.5}
        .workflow-phases{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.workflow-phases>div{padding:11px 9px;background:var(--bg-soft);border:1px solid var(--line-soft);border-radius:10px;display:grid;grid-template-columns:25px 1fr;gap:0 7px;align-items:center}.phase-icon{grid-row:1/3;width:23px;height:23px;border-radius:50%;display:grid;place-items:center;background:var(--panel-hi);font-size:11px;font-weight:800}.phase-icon.model{color:var(--violet)}.phase-icon.deterministic{color:var(--warn)}.phase-icon.record{color:var(--teal)}.workflow-phases b{font-size:12px}.workflow-phases small{font-size:10px;color:var(--text-mute);line-height:1.35}
        .workflow-progress{display:grid;gap:0;margin:2px 0 0}.workflow-progress li{display:grid;grid-template-columns:28px 1fr auto;gap:9px;align-items:center;padding:10px 0;border-top:1px solid var(--line-soft)}.workflow-progress li:first-child{border-top:0}.progress-dot{width:24px;height:24px;border-radius:8px;display:grid;place-items:center;background:var(--panel-hi);font-size:11px;font-weight:800}.workflow-progress .model .progress-dot{color:var(--violet)}.workflow-progress .deterministic .progress-dot{color:var(--warn)}.workflow-progress .record .progress-dot{color:var(--teal)}.workflow-progress .error .progress-dot{color:var(--crit)}.workflow-progress b{display:block;font-size:12px}.workflow-progress small{display:block;margin-top:2px;color:var(--text-mute);font-size:10px;text-transform:uppercase;letter-spacing:.06em}.progress-status{font-size:10px;color:var(--text-mute)}.workflow-progress .error .progress-status{color:var(--crit)}.workflow-next{grid-template-columns:20px 1fr!important;color:var(--text-mute);font-size:11px}.workflow-next .spinner{width:15px;height:15px}
        .workflow-foot{display:flex;gap:12px;flex-wrap:wrap;margin-top:14px;padding-top:12px;border-top:1px solid var(--line-soft);color:var(--text-mute);font-size:10px}.workflow-foot span:first-child{color:var(--teal)}
        @media(max-width:600px){.workflow-phases{grid-template-columns:1fr}.progress-status{display:none}}
      `}</style>
    </section>
  );
}
