import { useMemo, useState } from "react";
import GuardianAlert from "./GuardianAlert.jsx";

export default function AgentReview({ bundle, onApprove, busy, result }) {
  const [signNote, setSignNote] = useState(false);
  const [codeKeys, setCodeKeys] = useState([]);
  const [handoff, setHandoff] = useState(false);
  const [sendSummary, setSendSummary] = useState(false);
  const [orders, setOrders] = useState({});
  const codes = bundle.codes || [];
  const selectedCodes = useMemo(() => codes.filter((code) => codeKeys.includes(`${code.system}:${code.code}`)), [codes, codeKeys]);

  function toggleCode(key) {
    setCodeKeys((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key]);
  }

  function submit() {
    onApprove({
      sign_note: signNote,
      codes: selectedCodes.map(({ system, code }) => ({ system, code })),
      handoff,
      send_summary: sendSummary,
      orders,
    });
  }

  return (
    <section className="review-grid">
      <div className="review-head">
        <div><div className="eyebrow">Human review required</div><h2>Draft bundle</h2></div>
        <span className="pill">Facts/alerts recorded · actions need approval</span>
      </div>
      {(bundle.alerts || []).length > 0 && <div className="review-block critical-block"><h3>Guardian alerts</h3>{bundle.alerts.map((alert) => <GuardianAlert key={alert.id} alert={alert} />)}</div>}
      {bundle.note && <ReviewBlock title="Clinical note" checked={signNote} onChange={setSignNote} action="Sign note">
        <p>{bundle.note.summary || "No summary"}</p>
        <div className="draft-meta">{bundle.note.chief_complaint && <span>Chief complaint: {bundle.note.chief_complaint}</span>}{(bundle.note.follow_ups || []).map((item) => <span key={item}>Follow-up: {item}</span>)}</div>
      </ReviewBlock>}
      {codes.length > 0 && <div className="review-block"><h3>Billing codes <small>DRAFT · curated validation passed</small></h3>
        <div className="code-table">{codes.map((item) => { const key = `${item.system}:${item.code}`; return <label key={key} className="code-row"><input type="checkbox" checked={codeKeys.includes(key)} onChange={() => toggleCode(key)} /><b>{item.code}</b><span>{item.label}</span><q>{item.evidence}</q></label>; })}</div>
      </div>}
      {(bundle.staged_orders || []).length > 0 && <div className="review-block"><h3>Orders and medications <small>Choose an action</small></h3>
        {(bundle.staged_orders || []).map((item) => <div className={`order-row ${item.flagged ? "flagged" : ""}`} key={item.node_id}><span>{item.flagged ? "🔴" : "◌"} {item.label}</span><select className="select" value={orders[item.node_id] || ""} onChange={(event) => setOrders({ ...orders, [item.node_id]: event.target.value })}><option value="">Hold for review</option><option value="keep">Release / keep</option><option value="cancel">Cancel</option></select></div>)}
      </div>}
      {bundle.handoff && <ReviewBlock title="SBAR handoff" checked={handoff} onChange={setHandoff} action="Approve handoff"><p><b>Priority:</b> {bundle.handoff.priority_note}</p><p>{bundle.handoff.situation}</p></ReviewBlock>}
      {bundle.patient_summary && <ReviewBlock title="Patient summary" checked={sendSummary} onChange={setSendSummary} action="Send to patient"><p>{bundle.patient_summary}</p></ReviewBlock>}
      <div className="review-submit card"><div><b>Commit selected drafts</b><div className="muted">Unselected content remains a draft in the run audit.</div></div><button className="btn btn-primary" disabled={busy} onClick={submit}>{busy ? <span className="spinner" /> : "Approve selected"}</button></div>
      {result && <div className="approved-banner">✓ Approval recorded locally for encounter #{result.encounter_id}</div>}
      <style>{`
        .review-grid{display:grid;gap:14px}.review-head{display:flex;justify-content:space-between;align-items:end}.review-head h2{font-size:24px}.review-block{padding:18px;background:linear-gradient(180deg,var(--panel),var(--bg-soft));border:1px solid var(--line);border-radius:var(--radius)}
        .review-block h3{font-size:15px;margin-bottom:10px}.review-block h3 small{color:var(--text-mute);font-size:9px;letter-spacing:.08em;margin-left:8px}.critical-block{border-color:rgba(255,90,110,.5)}
        .review-block p{color:var(--text-dim);font-size:14px;margin-top:6px}.approval-check{display:flex;justify-content:space-between;gap:16px;align-items:start}.approval-check>label{display:flex;gap:8px;align-items:center;color:var(--teal);font-size:12px;font-weight:700;white-space:nowrap}
        .draft-meta{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}.draft-meta span{font-size:11px;padding:4px 7px;background:var(--panel-hi);border-radius:6px}.code-table{display:grid;gap:7px}.code-row{display:grid;grid-template-columns:20px 74px 1fr 1.2fr;gap:8px;align-items:center;padding:10px;background:var(--bg-soft);border:1px solid var(--line-soft);border-radius:9px;font-size:12px}.code-row q{color:var(--text-mute);font-style:italic}
        .order-row{display:grid;grid-template-columns:1fr 210px;align-items:center;gap:12px;padding:9px 0;border-top:1px solid var(--line-soft)}.order-row.flagged{color:var(--crit)}.order-row .select{padding:8px}.review-submit{padding:16px 18px;display:flex;justify-content:space-between;align-items:center}.review-submit .muted{font-size:12px}.approved-banner{padding:12px;border-radius:10px;background:rgba(62,224,138,.1);border:1px solid var(--ok);color:var(--ok);font-weight:700;font-size:13px}
        @media(max-width:700px){.review-head{align-items:start;gap:10px}.review-head .pill{display:none}.code-row{grid-template-columns:20px 70px 1fr}.code-row q{grid-column:2/4}.order-row{grid-template-columns:1fr}}
      `}</style>
    </section>
  );
}

function ReviewBlock({ title, checked, onChange, action, children }) {
  return <div className="review-block approval-check"><div><h3>{title} <small>DRAFT</small></h3>{children}</div><label><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} /> {action}</label></div>;
}
