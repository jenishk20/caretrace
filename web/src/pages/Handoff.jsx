import { useEffect, useState } from "react";
import { api } from "../api";
import { useApp } from "../context/AppContext";

export default function Handoff() {
  const { staff, patientId } = useApp();
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [latest, setLatest] = useState(null);
  const [history, setHistory] = useState([]);

  async function loadHistory() {
    setHistory(await api.listHandoffs(patientId));
  }

  useEffect(() => {
    loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId]);

  async function generate() {
    setError("");
    setStatus("Generating SBAR summary (may take a moment)...");
    try {
      const handoff = await api.generateHandoff(patientId, staff.id);
      setStatus("");
      setLatest(handoff);
      await loadHistory();
    } catch (err) {
      setStatus("");
      setError(err.message);
    }
  }

  return (
    <>
      <div className="card">
        <h2>Shift Handoff Generator</h2>
        <p className="muted">Synthesizes an SBAR summary from this patient's notes since the last handoff.</p>
        <button className="primary" onClick={generate}>
          Generate handoff
        </button>
        <div className="muted">{status}</div>
        {error && <div className="error">{error}</div>}
      </div>

      {latest && (
        <div className="card">
          <h3>Handoff — {latest.created_at}</h3>
          <p>
            <strong>Situation:</strong> {latest.situation}
          </p>
          <p>
            <strong>Background:</strong> {latest.background}
          </p>
          <p>
            <strong>Assessment:</strong> {latest.assessment}
          </p>
          <p>
            <strong>Recommendation:</strong> {latest.recommendation}
          </p>
        </div>
      )}

      <div className="card">
        <h3>Past handoffs</h3>
        {history.length ? (
          history.map((h) => (
            <div className="list-item" key={h.id}>
              {h.created_at} — {h.situation}
            </div>
          ))
        ) : (
          <p className="muted">No handoffs generated yet.</p>
        )}
      </div>
    </>
  );
}
