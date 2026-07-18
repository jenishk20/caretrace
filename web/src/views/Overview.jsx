import { useState } from "react";
import { api } from "../api";
import GraphView from "../components/GraphView.jsx";
import GuardianAlert from "../components/GuardianAlert.jsx";

export default function Overview({ patient, pid, snapshot, refresh, setTab }) {
  const [sel, setSel] = useState(null);
  const [ask, setAsk] = useState("");
  const [answer, setAnswer] = useState(null);
  const [asking, setAsking] = useState(false);
  const [sweeping, setSweeping] = useState(false);

  const alerts = snapshot.alerts || [];
  const activeAlerts = alerts.filter((a) => a.status === "active");
  const nodeCount = (snapshot.nodes || []).length;

  async function doAsk(q) {
    const question = q ?? ask;
    if (!question.trim()) return;
    setAsking(true);
    setAnswer(null);
    try {
      const res = await api.askRoom(pid, question, "staff");
      setAnswer(res);
    } catch (e) {
      setAnswer({ answer: "Could not reach the memory: " + e.message });
    } finally {
      setAsking(false);
    }
  }

  async function ackAlert(a, status) {
    await api.updateAlert(a.id, status);
    refresh();
  }

  async function sweep() {
    setSweeping(true);
    try {
      await api.guardianSweep(pid);
      await refresh();
    } finally {
      setSweeping(false);
    }
  }

  return (
    <div>
      <div className="row between" style={{ marginBottom: 4 }}>
        <div>
          <div className="muted" style={{ fontSize: 13 }}>Living record</div>
          <h1 style={{ fontSize: 26, letterSpacing: "-0.02em" }}>{patient.name}</h1>
        </div>
        <div className="row" style={{ gap: 10 }}>
          <span className="pill">{nodeCount} facts remembered</span>
          <button className="btn btn-primary" onClick={() => setTab("scribe")}>🎧 Capture a round</button>
        </div>
      </div>
      {patient.reason_for_visit && (
        <div className="muted" style={{ marginBottom: 18 }}>Here for: {patient.reason_for_visit}</div>
      )}

      <div className="ov-grid">
        {/* Graph centerpiece */}
        <div className="card" style={{ padding: 18, overflow: "hidden" }}>
          <div className="row between" style={{ marginBottom: 6 }}>
            <b>Live patient graph</b>
            <span className="muted" style={{ fontSize: 12 }}>Confide's memory — every interaction adds a node</span>
          </div>
          <GraphView snapshot={snapshot} height={430} onSelect={setSel} />
          {sel && (
            <div className="node-detail fade-up">
              <div className="row between">
                <b>{sel.label}</b>
                <span className="tag" style={{ background: "var(--panel-2)", color: "var(--text-dim)" }}>{sel.ntype}</span>
              </div>
              <div className="muted" style={{ fontSize: 13, marginTop: 6 }}>
                {sel.category ? `Category: ${sel.category} · ` : ""}
                {sel.polarity === "denied" ? "Patient denies · " : ""}
                {sel.status !== "active" ? `${sel.status} · ` : ""}
                Source: {sel.source_kind || "—"}
                {sel.confidence < 0.55 ? " · low confidence" : ""}
              </div>
              {sel.detail && <div style={{ fontSize: 13, marginTop: 4 }}>{sel.detail}</div>}
            </div>
          )}
          <Legend />
        </div>

        {/* Guardian + ask */}
        <div className="col" style={{ gap: 16 }}>
          <div className="card" style={{ padding: 18 }}>
            <div className="row between" style={{ marginBottom: 12 }}>
              <div className="row" style={{ gap: 8 }}>
                <span style={{ fontSize: 16 }}>🛡</span>
                <b>The Guardian</b>
              </div>
              <button className="btn btn-ghost" style={{ padding: "6px 10px", fontSize: 12 }} onClick={sweep} disabled={sweeping}>
                {sweeping ? <span className="spinner" /> : "Run sweep"}
              </button>
            </div>
            {activeAlerts.length === 0 && (
              <div className="muted" style={{ fontSize: 13, padding: "8px 0" }}>
                Watching. No open concerns — the Guardian speaks up on its own when something conflicts with the record.
              </div>
            )}
            <div className="col" style={{ gap: 10 }}>
              {activeAlerts.map((a) => (
                <GuardianAlert key={a.id} alert={a} onAck={(x) => ackAlert(x, "acknowledged")} onDismiss={(x) => ackAlert(x, "dismissed")} />
              ))}
            </div>
          </div>

          <div className="card" style={{ padding: 18 }}>
            <div className="row" style={{ gap: 8, marginBottom: 10 }}>
              <span style={{ fontSize: 16 }}>💬</span>
              <b>Ask the room</b>
            </div>
            <p className="muted" style={{ fontSize: 12, marginBottom: 10 }}>Ask the patient's history out loud — answered from the graph.</p>
            <div className="row" style={{ gap: 8 }}>
              <input className="input" placeholder="What was her pain at admission?" value={ask}
                onChange={(e) => setAsk(e.target.value)} onKeyDown={(e) => e.key === "Enter" && doAsk()} />
              <button className="btn btn-primary" onClick={() => doAsk()} disabled={asking}>
                {asking ? <span className="spinner" /> : "Ask"}
              </button>
            </div>
            <div className="row wrap" style={{ gap: 6, marginTop: 10 }}>
              {["What are her allergies?", "Is she on any blood thinners?", "Why is she here?"].map((q) => (
                <button key={q} className="chip" onClick={() => { setAsk(q); doAsk(q); }}>{q}</button>
              ))}
            </div>
            {answer && (
              <div className="answer fade-up">
                <span style={{ color: "var(--teal)", fontSize: 12, fontWeight: 700 }}>◈ CONFIDE</span>
                <div style={{ marginTop: 4 }}>{answer.answer}</div>
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`
        .ov-grid { display:grid; grid-template-columns:1.35fr 1fr; gap:16px; align-items:start; }
        .node-detail { margin-top:10px; background:var(--bg-soft); border:1px solid var(--line);
          border-radius:10px; padding:12px 14px; }
        .answer { margin-top:12px; background:rgba(47,230,200,0.06); border:1px solid var(--teal-dim);
          border-radius:10px; padding:12px 14px; font-size:14px; line-height:1.55; }
        .chip { font-size:12px; padding:6px 11px; border-radius:999px; background:var(--panel-2);
          border:1px solid var(--line); color:var(--text-dim); }
        .chip:hover { border-color:var(--teal-dim); color:var(--text); }
        @media (max-width:960px){ .ov-grid{grid-template-columns:1fr;} }
      `}</style>
    </div>
  );
}

function Legend() {
  const items = [
    ["℞", "Medication", "#5b8cff"], ["⚠", "Allergy", "#ff5a6e"], ["＋", "Symptom", "#ff9db0"],
    ["◆", "Condition", "#ffb84d"], ["🧪", "Order", "#2fe6c8"], ["❝", "Statement", "#8a97bd"],
  ];
  return (
    <div className="row wrap" style={{ gap: 12, marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--line-soft)" }}>
      {items.map(([ic, label, c]) => (
        <span key={label} className="row" style={{ gap: 5, fontSize: 11, color: "var(--text-mute)" }}>
          <span style={{ color: c }}>{ic}</span>{label}
        </span>
      ))}
      <span className="row" style={{ gap: 5, fontSize: 11, color: "var(--text-mute)" }}>
        <span style={{ color: "var(--crit)" }}>—</span>conflict
      </span>
    </div>
  );
}
