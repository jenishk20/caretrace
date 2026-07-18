import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import ConsentView from "./ConsentView.jsx";
import ScribeView from "./ScribeView.jsx";
import HandoffView from "./HandoffView.jsx";
import DischargeView from "./DischargeView.jsx";
import PrescriptionStep from "./PrescriptionStep.jsx";
import GraphView from "../components/GraphView.jsx";
import GuardianAlert from "../components/GuardianAlert.jsx";

// The guided visit — one journey from the patient walking in to walking out. Each stage
// reuses the same feature view a power user would open directly, but sequenced so a new
// clinician is led through Hear → Remember → Watch, start to finish. State is derived from
// the record, so the rail always reflects what's actually been done this visit.

const STAGES = [
  { key: "prepare", label: "Prepare", icon: "◈", blurb: "Who's in the room, and what Confide already knows." },
  { key: "consent", label: "Consent", icon: "📋", blurb: "Explain the form in her language, log that she understood." },
  { key: "meeting", label: "The meeting", icon: "🎧", blurb: "Capture the round — the graph grows and the Guardian watches." },
  { key: "prescription", label: "Prescription", icon: "℞", blurb: "Add the prescription to the record — checked against her allergies." },
  { key: "handoff", label: "Handoff", icon: "🔀", blurb: "Write the whole stay up for the next clinician." },
  { key: "discharge", label: "Discharge", icon: "🏠", blurb: "The going-home plan, with red flags and reminders." },
];

export default function VisitFlow({ patient, pid, staff, snapshot, refresh, setTab }) {
  const [step, setStep] = useState(0);
  const [done, setDone] = useState({});

  // Derive which stages are complete from real data (not click history).
  const computeDone = useCallback(async () => {
    const [consent, encounters, rx, handoffs] = await Promise.all([
      api.consentList(pid).catch(() => []),
      api.scribeEncounters(pid).catch(() => []),
      api.prescriptionList(pid).catch(() => []),
      api.handoffHistory(pid).catch(() => []),
    ]);
    setDone({
      consent: consent.length > 0,
      meeting: encounters.length > 0,
      prescription: rx.length > 0,
      handoff: handoffs.length > 0,
      discharge: patient.status === "discharged",
    });
  }, [pid, patient.status]);

  useEffect(() => { computeDone(); }, [computeDone, snapshot]);

  const shared = { patient, pid, staff, snapshot, refresh, setTab };
  const stage = STAGES[step];
  const activeAlerts = (snapshot.alerts || []).filter((a) => a.status === "active");

  const go = (i) => setStep(Math.max(0, Math.min(STAGES.length - 1, i)));

  return (
    <div className="vf">
      <div className="row between" style={{ marginBottom: 4 }}>
        <div>
          <div className="muted" style={{ fontSize: 13 }}>Guided visit</div>
          <h1 style={{ fontSize: 26, letterSpacing: "-0.02em" }}>{patient.name}</h1>
        </div>
        <div className="row" style={{ gap: 10 }}>
          {activeAlerts.length > 0 && (
            <span className="pill" style={{ color: "var(--crit)", borderColor: "var(--crit)" }}>
              🛡 {activeAlerts.length} open
            </span>
          )}
          <span className={`pill ${patient.status === "discharged" ? "" : ""}`}>{patient.status}</span>
        </div>
      </div>

      {/* Journey rail */}
      <div className="rail">
        {STAGES.map((s, i) => {
          const complete = done[s.key];
          const active = i === step;
          return (
            <button key={s.key} className={`rail-node ${active ? "on" : ""} ${complete ? "done" : ""}`} onClick={() => go(i)}>
              <span className="rn-dot">{complete && !active ? "✓" : s.icon}</span>
              <span className="rn-label">{s.label}</span>
              {i < STAGES.length - 1 && <span className="rn-line" />}
            </button>
          );
        })}
      </div>
      <p className="muted rail-blurb">{stage.blurb}</p>

      {/* Stage body — reuse the real feature views */}
      <div className="vf-body fade-up" key={stage.key}>
        {stage.key === "prepare" && <PrepareStep {...shared} activeAlerts={activeAlerts} />}
        {stage.key === "consent" && <ConsentView {...shared} />}
        {stage.key === "meeting" && <ScribeView {...shared} />}
        {stage.key === "prescription" && <PrescriptionStep {...shared} onChange={computeDone} />}
        {stage.key === "handoff" && <HandoffView {...shared} />}
        {stage.key === "discharge" && <DischargeStep {...shared} onChange={computeDone} />}
      </div>

      {/* Nav */}
      <div className="row between vf-nav">
        <button className="btn btn-ghost" onClick={() => go(step - 1)} disabled={step === 0}>← Back</button>
        <span className="muted" style={{ fontSize: 13 }}>Step {step + 1} of {STAGES.length}</span>
        <button className="btn btn-primary" onClick={() => go(step + 1)} disabled={step === STAGES.length - 1}>
          Next: {STAGES[Math.min(step + 1, STAGES.length - 1)].label} →
        </button>
      </div>

      <style>{`
        .rail { display:flex; align-items:flex-start; gap:0; margin:18px 0 2px; overflow-x:auto; padding-bottom:4px; }
        .rail-node { position:relative; display:flex; flex-direction:column; align-items:center; gap:7px;
          min-width:104px; flex:1; color:var(--text-mute); }
        .rn-dot { width:38px; height:38px; border-radius:12px; display:grid; place-items:center; font-size:16px;
          background:var(--panel); border:1px solid var(--line); z-index:2; transition:all 0.16s; }
        .rail-node.on .rn-dot { background:var(--panel-hi); border-color:var(--teal); color:var(--teal);
          box-shadow:0 0 0 4px var(--teal-glow); }
        .rail-node.done .rn-dot { border-color:var(--teal-dim); color:var(--teal); }
        .rn-label { font-size:12px; font-weight:600; }
        .rail-node.on .rn-label { color:var(--text); }
        .rn-line { position:absolute; top:19px; left:50%; width:100%; height:2px; background:var(--line); z-index:1; }
        .rail-node.done .rn-line { background:var(--teal-dim); }
        .rail-blurb { margin:6px 0 18px; font-size:14px; }
        .vf-nav { margin-top:24px; padding-top:16px; border-top:1px solid var(--line-soft); }
      `}</style>
    </div>
  );
}

// --- Prepare: patient at-a-glance + what's already known ----------------------
function PrepareStep({ patient, snapshot, activeAlerts }) {
  const nodes = snapshot.nodes || [];
  const allergies = nodes.filter((n) => n.ntype === "allergy");
  const meds = nodes.filter((n) => n.ntype === "medication");
  return (
    <div className="prep-grid">
      <div className="col" style={{ gap: 14 }}>
        <div className="card" style={{ padding: 18 }}>
          <b>At admission</b>
          <div className="prep-facts">
            <Fact label="Age" value={patient.age ? `${patient.age} yrs` : "—"} />
            <Fact label="Room" value={patient.room || "—"} />
            <Fact label="Language" value={patient.primary_language || "en"} />
            <Fact label="MRN" value={patient.mrn || "—"} />
          </div>
          {patient.reason_for_visit && (
            <div className="prep-reason">Here for: <b>{patient.reason_for_visit}</b></div>
          )}
        </div>
        <div className="card" style={{ padding: 18 }}>
          <b style={{ fontSize: 14 }}>Known before she said a word</b>
          <div className="row wrap" style={{ gap: 6, marginTop: 10 }}>
            {allergies.length === 0 && meds.length === 0 && <span className="muted">Nothing on record yet.</span>}
            {allergies.map((a) => (
              <span key={a.id} className="tag" style={{ background: "rgba(255,90,110,0.12)", color: "var(--crit)" }}>⚠ {a.label}</span>
            ))}
            {meds.map((m) => (
              <span key={m.id} className="tag" style={{ background: "rgba(91,140,255,0.12)", color: "var(--blue)" }}>℞ {m.label}</span>
            ))}
          </div>
          {activeAlerts.length > 0 && (
            <div className="col" style={{ gap: 8, marginTop: 12 }}>
              {activeAlerts.slice(0, 2).map((a) => <GuardianAlert key={a.id} alert={a} />)}
            </div>
          )}
        </div>
      </div>
      <div className="card" style={{ padding: 16, overflow: "hidden" }}>
        <div className="row between" style={{ marginBottom: 6 }}>
          <b style={{ fontSize: 14 }}>Living graph</b>
          <span className="muted" style={{ fontSize: 12 }}>{nodes.length} facts</span>
        </div>
        <GraphView snapshot={snapshot} height={330} />
      </div>
      <style>{`
        .prep-grid { display:grid; grid-template-columns:1fr 1.1fr; gap:16px; align-items:start; }
        .prep-facts { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:12px; }
        .prep-reason { margin-top:14px; padding:10px 12px; background:var(--bg-soft); border:1px solid var(--line-soft);
          border-radius:8px; font-size:14px; }
        @media(max-width:960px){ .prep-grid{grid-template-columns:1fr;} }
      `}</style>
    </div>
  );
}

function Fact({ label, value }) {
  return (
    <div>
      <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
      <div style={{ marginTop: 2, fontWeight: 600 }}>{value}</div>
    </div>
  );
}

// --- Discharge stage: the navigator + the actual discharge action ------------
function DischargeStep({ onChange, ...shared }) {
  const { patient, pid, refresh } = shared;
  const [busy, setBusy] = useState(false);
  async function discharge() {
    if (!confirm(`Discharge ${patient.name}? Confide will keep the full record.`)) return;
    setBusy(true);
    try {
      await api.dischargePatient(pid);
      await refresh();
      onChange?.();
    } finally { setBusy(false); }
  }
  return (
    <div>
      <DischargeView {...shared} />
      <div className="card" style={{ padding: 18, marginTop: 16, borderColor: patient.status === "discharged" ? "var(--ok)" : "var(--line)" }}>
        <div className="row between">
          <div>
            <b>{patient.status === "discharged" ? "Discharged" : "Ready to go home?"}</b>
            <div className="muted" style={{ fontSize: 13, marginTop: 2 }}>
              {patient.status === "discharged"
                ? "The record stays — reopen any time from the roster."
                : "Marks the visit complete. The living record is preserved for the next visit."}
            </div>
          </div>
          {patient.status === "discharged" ? (
            <span className="tag" style={{ background: "rgba(62,224,138,0.12)", color: "var(--ok)" }}>complete</span>
          ) : (
            <button className="btn btn-danger" onClick={discharge} disabled={busy}>
              {busy ? <span className="spinner" /> : "Discharge patient"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
