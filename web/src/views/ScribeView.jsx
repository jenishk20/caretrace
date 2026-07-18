import { useState } from "react";
import { api } from "../api";
import RecordButton from "../components/RecordButton.jsx";
import GuardianAlert from "../components/GuardianAlert.jsx";
import GraphView from "../components/GraphView.jsx";

// Scripted demo lines — one tap to reproduce each Guardian beat every time.
const SCRIPTS = [
  { label: "Contradiction + allergy + order", text: "Patient tells me she is not on any blood thinners. I'd like to start her on amoxicillin for the infection. Also please recheck her troponin in two hours." },
  { label: "Interaction (warfarin + NSAID)", text: "Let's add ibuprofen for her pain and continue the warfarin." },
  { label: "Plain round note", text: "Patient resting comfortably, pain down to 3 out of 10. Continue current plan, reassess in the morning." },
];

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
        Dictate or type what's said. Confide structures the note, grows the graph, and the Guardian
        checks it against the record — in one pass.
      </p>

      <div className="sc-grid">
        <div className="col" style={{ gap: 16 }}>
          <div className="card" style={{ padding: 18 }}>
            <RecordButton onText={capture} cta="Capture & analyze" placeholder="Dictate the round, or type what was said…" />
            <div className="sep" />
            <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>SCRIPTED DEMO LINES</div>
            <div className="col" style={{ gap: 8 }}>
              {SCRIPTS.map((s) => (
                <button key={s.label} className="script" onClick={() => capture(s.text)} disabled={busy}>
                  <b style={{ fontSize: 13 }}>{s.label}</b>
                  <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>{s.text}</div>
                </button>
              ))}
            </div>
          </div>

          {busy && (
            <div className="card thinking" style={{ padding: 20 }}>
              <span className="spinner" />
              <div>
                <b>Confide is listening…</b>
                <div className="muted" style={{ fontSize: 13 }}>Structuring the note · extracting facts · running the Guardian</div>
              </div>
            </div>
          )}

          {result && (
            <div className="card fade-up" style={{ padding: 18 }}>
              <b>Structured note</b>
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
        </div>

        <div className="col" style={{ gap: 16 }}>
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
          <div className="card" style={{ padding: 16, overflow: "hidden" }}>
            <div className="row between" style={{ marginBottom: 6 }}>
              <b style={{ fontSize: 14 }}>Graph</b>
              <span className="muted" style={{ fontSize: 12 }}>{(snapshot.nodes || []).length} facts</span>
            </div>
            <GraphView snapshot={snapshot} height={320} />
          </div>
        </div>
      </div>

      <style>{`
        .sc-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; align-items:start; }
        .script { text-align:left; padding:12px 14px; background:var(--bg-soft); border:1px solid var(--line);
          border-radius:10px; transition:all 0.13s; }
        .script:hover { border-color:var(--teal-dim); }
        .thinking { display:flex; gap:14px; align-items:center; border-color:var(--teal-dim); }
        .note-block { display:flex; flex-direction:column; gap:12px; }
        @media (max-width:960px){ .sc-grid{grid-template-columns:1fr;} }
      `}</style>
    </div>
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
