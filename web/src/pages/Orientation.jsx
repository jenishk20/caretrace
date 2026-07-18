import { useState } from "react";
import { api } from "../api";
import { useApp } from "../context/AppContext";

export default function Orientation() {
  const { staff, patientId } = useApp();
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  async function generate() {
    setError("");
    setStatus("Generating orientation script (may take a moment)...");
    try {
      const res = await api.generateOrientation(patientId, staff.id);
      setStatus("");
      setResult(res);
    } catch (err) {
      setStatus("");
      setError(err.message);
    }
  }

  async function replay() {
    setError("");
    try {
      setResult(await api.latestOrientation(patientId));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="card">
      <h2>Bedside Orientation</h2>
      <p className="muted">A gentle spoken reminder of day, location, reason for stay, and what's next.</p>
      <button className="primary" onClick={generate}>
        Play orientation
      </button>
      <button onClick={replay}>Replay last</button>
      <div className="muted">{status}</div>
      {error && <div className="error">{error}</div>}
      {result && (
        <div style={{ marginTop: 16 }}>
          <p>{result.script_text}</p>
          {result.audio_url && <audio controls autoPlay src={result.audio_url} />}
        </div>
      )}
    </div>
  );
}
