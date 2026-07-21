import { useState } from "react";
import { api } from "../api";
import RecordButton from "../components/RecordButton.jsx";
import GuardianAlert from "../components/GuardianAlert.jsx";
import GraphView from "../components/GraphView.jsx";

export default function ScribeView({ pid, staff, snapshot, refresh }) {
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [liveAlerts, setLiveAlerts] = useState([]);

  async function capture(text) {
    setBusy(true);
    setResult(null);
    setLiveAlerts([]);
    try {
      const res = await api.scribeCapture({ patient_id: pid, staff_id: staff?.staff_id, transcript: text, kind: "round" });
      setResult(res);
      setLiveAlerts(res.alerts || []);
      await refresh();
    } catch (e) {
      alert("Capture failed: " + e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="muted" style={{ fontSize: 13 }}>Clinical Scribe · Hear</div>
      <h1 style={{ fontSize: 26, letterSpacing: "-0.02em", marginBottom: 4 }}>Capture the encounter</h1>
      <p className="muted" style={{ marginBottom: 20 }}>
        Dictate or type what's said. CareTrace structures the note, grows the graph, and the Guardian
        checks it against the record — in one pass.
      </p>

      <div className="sc-grid">
        <div className="col" style={{ gap: 16 }}>
          <div className="card sc-capture" style={{ padding: 18 }}>
            <RecordButton grow onText={capture} cta="Capture & analyze" placeholder="Dictate the round, or type what was said…" />
          </div>

          {busy && (
            <div className="card thinking" style={{ padding: 20 }}>
              <span className="spinner" />
              <div>
                <b>CareTrace is thinking…</b>
                <div className="muted" style={{ fontSize: 13 }}>Structuring the note · extracting facts · running the Guardian</div>
              </div>
            </div>
          )}

          {result && (
            <div className="card fade-up" style={{ padding: 18 }}>
              <div className="row between">
                <b>Structured note</b>
                <ToneChip tone={result.note.emotional_tone} />
              </div>
              <div className="note-block" style={{ marginTop: 12 }}>
                <Field label="Chief complaint" value={result.note.chief_complaint} />
                <Field label="Summary" value={result.note.summary} />
                <ListField label="Medications" items={result.note.medications} />
                <ListField label="Follow-ups" items={result.note.follow_ups} />
              </div>
              <div className="sep" />
              <div className="muted" style={{ fontSize: 12 }}>
                + {(result.new_nodes || []).length} new facts added to the graph
              </div>
            </div>
          )}
          {liveAlerts.length > 0 && (
            <div className="col" style={{ gap: 10 }}>
              <div className="row" style={{ gap: 8 }}>
                <span style={{ fontSize: 16 }}>🛡</span>
                <b>The Guardian spoke up</b>
              </div>
              {liveAlerts.map((a) => (
                <GuardianAlert key={a.id} alert={a} live />
              ))}
            </div>
          )}
        </div>

        <div className="card graph-card">
          <div className="row between" style={{ marginBottom: 8 }}>
            <div className="row" style={{ gap: 8 }}>
              <span style={{ color: "var(--teal)" }}>◈</span>
              <b style={{ fontSize: 14 }}>Live patient graph</b>
            </div>
            <span className="muted" style={{ fontSize: 12 }}>{(snapshot.nodes || []).length} facts · ⤢ to expand</span>
          </div>
          <GraphView snapshot={snapshot} height={520} />
        </div>
      </div>

      <style>{`
        .sc-grid { display:grid; grid-template-columns:minmax(320px, 400px) 1fr; gap:16px; align-items:start; }
        /* Match the dictation card to the graph's height so the two sides balance. */
        .sc-capture { min-height:520px; display:flex; flex-direction:column; }
        .thinking { display:flex; gap:14px; align-items:center; border-color:var(--teal-dim); }
        .note-block { display:flex; flex-direction:column; gap:12px; }
        .graph-card { padding:16px; overflow:hidden; position:sticky; top:24px; }
        @media (max-width:1040px){ .sc-grid{grid-template-columns:1fr;} .graph-card{position:static;}
          .sc-capture{min-height:280px;} }
      `}</style>
    </div>
  );
}

// GPT-OSS-inferred patient affect for the round. Color-coded so a distressed
// patient reads at a glance without changing the note layout.
const TONE_COLORS = {
  anxious: "#ffb84d", distressed: "#ff5a6e", "in pain": "#ff5a6e",
  frustrated: "#ff9db0", calm: "#3ee08a", reassured: "#3ee08a", neutral: "#8a97bd",
};

export function ToneChip({ tone }) {
  if (!tone) return null;
  const c = TONE_COLORS[String(tone).toLowerCase()] || "#8a97bd";
  return (
    <span className="row" style={{ gap: 6, fontSize: 12, padding: "4px 10px", borderRadius: 999,
      background: "var(--panel-2)", border: "1px solid var(--line)", color: "var(--text-dim)" }}>
      <span style={{ width: 7, height: 7, borderRadius: 999, background: c, display: "inline-block" }} />
      {tone}
    </span>
  );
}

function Field({ label, value }) {
  return (
    <div>
      <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
      <div style={{ marginTop: 2 }}>{value || <span className="muted">—</span>}</div>
    </div>
  );
}

function ListField({ label, items }) {
  return (
    <div>
      <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
      {items && items.length ? (
        <ul style={{ marginTop: 4, paddingLeft: 18 }}>
          {items.map((it, i) => <li key={i} style={{ fontSize: 14 }}>{it}</li>)}
        </ul>
      ) : <div className="muted" style={{ marginTop: 2 }}>—</div>}
    </div>
  );
}
