import { useEffect, useState } from "react";
import { api } from "../api";
import { useApp } from "../context/AppContext";
import RecordButton from "../components/RecordButton";

export default function Translate() {
  const { staff, patientId, patient } = useApp();
  const [direction, setDirection] = useState("staff_to_patient");
  const [targetLang, setTargetLang] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    if (patient) setTargetLang(patient.primary_language === "en" ? "Spanish" : "English");
  }, [patient]);

  async function loadLogs() {
    setLogs(await api.listTranslationLogs(patientId));
  }

  useEffect(() => {
    loadLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId]);

  async function handleRecorded(blob) {
    setStatus("Transcribing and translating...");
    setError("");
    try {
      const res = await api.translateTurn(blob, {
        patient_id: patientId,
        staff_id: staff.id,
        direction,
        target_language: targetLang,
      });
      setResult(res);
      setStatus("");
      await loadLogs();
    } catch (err) {
      setStatus("");
      setError(err.message);
    }
  }

  return (
    <>
      <div className="card">
        <h2>Real-Time Translation</h2>
        <div className="row">
          <div>
            <label>Direction</label>
            <select value={direction} onChange={(e) => setDirection(e.target.value)}>
              <option value="staff_to_patient">Staff → Patient</option>
              <option value="patient_to_staff">Patient → Staff</option>
            </select>
          </div>
          <div>
            <label>Target language</label>
            <input value={targetLang} onChange={(e) => setTargetLang(e.target.value)} />
          </div>
        </div>
        <RecordButton idleLabel="Record turn" recordingLabel="Stop" onStop={handleRecorded} />
        <div className="muted">{status}</div>

        {result && (
          <div style={{ marginTop: 16 }}>
            <p>
              <strong>Heard:</strong> {result.source_text} <span className="muted">({result.source_language})</span>
            </p>
            <p>
              <strong>Translated:</strong> {result.translated_text}
            </p>
            <audio controls autoPlay src={result.audio_url} />
          </div>
        )}
        {error && <div className="error">{error}</div>}
      </div>

      <div className="card">
        <h3>Conversation log</h3>
        {logs.length ? (
          logs.map((l) => (
            <div className="list-item" key={l.id}>
              <span className="muted">[{l.direction}]</span> {l.source_text} → <strong>{l.translated_text}</strong>
            </div>
          ))
        ) : (
          <p className="muted">No turns recorded yet.</p>
        )}
      </div>
    </>
  );
}
