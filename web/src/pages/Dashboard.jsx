import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useApp } from "../context/AppContext";

const FEATURES = [
  ["/scribe", "Clinical Scribe"],
  ["/translate", "Real-Time Translation"],
  ["/consent", "Consent Explainer"],
  ["/discharge", "Discharge Navigator"],
  ["/handoff", "Shift Handoff"],
  ["/orientation", "Bedside Orientation"],
];

export default function Dashboard() {
  const { staff, patientId, patient, refreshPatient } = useApp();
  const [notes, setNotes] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [dischargeError, setDischargeError] = useState("");

  useEffect(() => {
    if (!patientId) return;
    api.listNotes(patientId).then(setNotes);
    api.listReminders(patientId, "pending").then(setReminders);
  }, [patientId]);

  if (!patient) return <p className="muted">Loading patient...</p>;

  async function discharge() {
    if (!confirm(`Discharge ${patient.name}?`)) return;
    try {
      await api.dischargePatient(patientId, staff.id);
      refreshPatient();
    } catch (err) {
      setDischargeError(err.message);
    }
  }

  return (
    <>
      <div className="card">
        <h2>
          {patient.name} <span className="muted">({patient.status})</span>
        </h2>
        <p className="muted">
          Room {patient.room || "-"} · MRN {patient.mrn || "-"} · Language {patient.primary_language}
          {patient.known_allergies ? ` · Allergies: ${patient.known_allergies}` : ""}
        </p>
        {patient.status === "admitted" ? (
          <button className="danger" onClick={discharge}>
            Discharge patient
          </button>
        ) : (
          <span className="badge ok">Discharged {patient.discharged_at || ""}</span>
        )}
        {dischargeError && <div className="error">{dischargeError}</div>}
      </div>

      <div className="card">
        <h3>Features</h3>
        <div className="feature-grid">
          {FEATURES.map(([path, label]) => (
            <Link key={path} to={path}>
              <button style={{ width: "100%" }}>{label}</button>
            </Link>
          ))}
        </div>
      </div>

      <div className="card">
        <h3>Latest note</h3>
        {notes.length ? (
          <>
            <p>
              <strong>Chief complaint:</strong> {notes[0].chief_complaint || "-"}
            </p>
            <p className="muted">
              {notes[0].status} · {notes[0].created_at}
            </p>
          </>
        ) : (
          <p className="muted">No notes recorded yet.</p>
        )}
      </div>

      <div className="card">
        <h3>Pending reminders</h3>
        {reminders.length ? (
          reminders.map((r) => (
            <div className="list-item" key={r.id}>
              {r.description} <span className="muted">— {r.remind_at}</span>
            </div>
          ))
        ) : (
          <p className="muted">No pending reminders.</p>
        )}
      </div>
    </>
  );
}
