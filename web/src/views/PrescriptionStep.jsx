import { useEffect, useState } from "react";
import { api } from "../api";
import GuardianAlert from "../components/GuardianAlert.jsx";

const SAMPLE = `Rx — COMMUNITY PHARMACY

Patient: María González
Amoxicillin 500 mg capsules
Take 1 capsule by mouth three times daily for 7 days.
Quantity: 21    Refills: 0`;

// Prescription = a document upload for the portal, but its medications are routed into the
// graph so the Guardian checks them against her allergies. That's the beat: prescribe
// amoxicillin for a penicillin-allergic patient and the alert fires on its own.
export default function PrescriptionStep({ pid, staff, refresh, onChange }) {
  const [ocr, setOcr] = useState(SAMPLE);
  const [busy, setBusy] = useState(false);
  const [doc, setDoc] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [history, setHistory] = useState([]);

  const load = () => api.prescriptionList(pid).then(setHistory).catch(() => {});
  useEffect(() => { load(); }, [pid]);

  async function ingest(result) {
    setDoc(result);
    setAlerts(result.alerts || []);
    await refresh();
    load();
    onChange?.();
  }

  async function submitText() {
    setBusy(true);
    try { await ingest(await api.prescriptionText({ patient_id: pid, staff_id: staff?.staff_id, ocr_text: ocr })); }
    catch (e) { alert(e.message); } finally { setBusy(false); }
  }

  async function uploadImg(file) {
    setBusy(true);
    try {
      const d = await api.prescriptionImage(pid, staff?.staff_id, file);
      setOcr(d.ocr_text || "");
      await ingest(d);
    } catch (e) { alert(e.message); } finally { setBusy(false); }
  }

  return (
    <div>
      <div className="muted" style={{ fontSize: 13 }}>Prescription · Watch</div>
      <h1 style={{ fontSize: 26, letterSpacing: "-0.02em", marginBottom: 4 }}>Add the prescription</h1>
      <p className="muted" style={{ marginBottom: 20 }}>
        Upload or paste the prescription. Confide files it to the portal and adds its medications to
        the living record — where the Guardian checks them against her allergies before you leave the room.
      </p>

      <div className="rx-grid">
        <div className="card" style={{ padding: 18 }}>
          <div className="row between" style={{ marginBottom: 10 }}>
            <b style={{ fontSize: 14 }}>Prescription</b>
            <label className="btn btn-ghost" style={{ padding: "6px 10px", fontSize: 12 }}>
              📷 Photo
              <input type="file" accept="image/*" style={{ display: "none" }}
                onChange={(e) => e.target.files[0] && uploadImg(e.target.files[0])} />
            </label>
          </div>
          <textarea className="textarea" style={{ minHeight: 200, fontFamily: "var(--mono)", fontSize: 12 }}
            value={ocr} onChange={(e) => setOcr(e.target.value)} />
          <button className="btn btn-primary" style={{ marginTop: 12, width: "100%", justifyContent: "center" }}
            onClick={submitText} disabled={busy}>
            {busy ? <span className="spinner" /> : "Add to record"}
          </button>
        </div>

        <div className="col" style={{ gap: 16 }}>
          {alerts.length > 0 && (
            <div className="col" style={{ gap: 10 }}>
              <div className="row" style={{ gap: 8 }}><span style={{ fontSize: 16 }}>🛡</span><b>The Guardian spoke up</b></div>
              {alerts.map((a) => <GuardianAlert key={a.id} alert={a} live />)}
            </div>
          )}

          {doc && (
            <div className="card fade-up" style={{ padding: 18 }}>
              <div className="row" style={{ gap: 8, marginBottom: 10 }}><span style={{ fontSize: 16 }}>◈</span><b>In plain language</b></div>
              <div style={{ fontSize: 15, lineHeight: 1.6 }}>{doc.explanation}</div>
              {doc.medications?.length > 0 && (
                <>
                  <div className="sep" />
                  <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>ADDED TO THE RECORD</div>
                  <div className="col" style={{ gap: 6 }}>
                    {doc.medications.map((m, i) => (
                      <div key={i} className="row between rx-med">
                        <b style={{ fontSize: 13 }}>℞ {m.name}</b>
                        {m.schedule && <span className="muted" style={{ fontSize: 12 }}>{m.schedule}</span>}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {history.length > 0 && (
            <div className="card" style={{ padding: 18 }}>
              <b style={{ fontSize: 14 }}>On file</b>
              <div className="col" style={{ gap: 6, marginTop: 10 }}>
                {history.map((h) => (
                  <div key={h.id} className="muted" style={{ fontSize: 13 }}>
                    ℞ {fmt(h.created_at)} — {(h.explanation || h.ocr_text || "").slice(0, 60)}…
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        .rx-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; align-items:start; }
        .rx-med { padding:9px 12px; background:var(--bg-soft); border:1px solid var(--line-soft); border-radius:8px; }
        @media(max-width:960px){ .rx-grid{grid-template-columns:1fr;} }
      `}</style>
    </div>
  );
}

function fmt(iso) {
  try { return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); }
  catch { return iso; }
}
