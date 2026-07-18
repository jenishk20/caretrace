import { useEffect, useState } from "react";
import { api } from "../api";
import { useApp } from "../context/AppContext";
import RecordButton from "../components/RecordButton";

export default function Scribe() {
  const { staff, patientId } = useApp();
  const [transcript, setTranscript] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [medications, setMedications] = useState("");
  const [followUps, setFollowUps] = useState("");
  const [noteId, setNoteId] = useState(null);
  const [notes, setNotes] = useState([]);

  async function loadNotes() {
    setNotes(await api.listNotes(patientId));
  }

  useEffect(() => {
    loadNotes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId]);

  async function handleRecorded(blob) {
    setStatus("Transcribing...");
    setError("");
    try {
      const { transcript: t } = await api.transcribe(blob);
      setTranscript(t);
      setStatus("Transcribed. Edit if needed, then structure.");
    } catch (err) {
      setStatus("");
      setError(err.message);
    }
  }

  async function structureNote() {
    setError("");
    if (!transcript.trim()) {
      setError("Record or type a transcript first.");
      return;
    }
    setStatus("Structuring note (calls the local model, may take a moment)...");
    try {
      const structured = await api.structureTranscript(transcript);
      setChiefComplaint(structured.chief_complaint || "");
      setMedications((structured.medications || []).join("\n"));
      setFollowUps((structured.follow_ups || []).join("\n"));
      setShowForm(true);
      setNoteId(null);
      setStatus("Structured. Review and save.");
    } catch (err) {
      setStatus("");
      setError(err.message);
    }
  }

  function noteBody(status_) {
    return {
      patient_id: patientId,
      staff_id: staff.id,
      raw_transcript: transcript,
      chief_complaint: chiefComplaint,
      medications: medications.split("\n").filter(Boolean),
      follow_ups: followUps.split("\n").filter(Boolean),
      status: status_,
    };
  }

  async function saveNote(status_) {
    setError("");
    try {
      if (noteId) {
        await api.updateNote(noteId, noteBody(status_));
      } else {
        const note = await api.createNote(noteBody(status_));
        setNoteId(note.id);
      }
      setStatus(status_ === "finalized" ? "Note finalized." : "Draft saved.");
      await loadNotes();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <div className="card">
        <h2>Clinical Scribe</h2>
        <p className="muted">Record rounds dictation. It will be transcribed and structured locally.</p>
        <RecordButton idleLabel="Record dictation" recordingLabel="Stop recording" onStop={handleRecorded} />
        <div className="muted">{status}</div>
        <textarea
          rows={4}
          placeholder="Transcript will appear here — you can also type/edit directly"
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
        />
        <button onClick={structureNote}>Structure note</button>

        {showForm && (
          <div style={{ marginTop: 16 }}>
            <label>Chief complaint</label>
            <input value={chiefComplaint} onChange={(e) => setChiefComplaint(e.target.value)} />
            <label>Medications (one per line)</label>
            <textarea rows={3} value={medications} onChange={(e) => setMedications(e.target.value)} />
            <label>Follow-ups (one per line)</label>
            <textarea rows={3} value={followUps} onChange={(e) => setFollowUps(e.target.value)} />
            <button className="primary" onClick={() => saveNote("draft")}>
              Save draft
            </button>
            <button onClick={() => saveNote("finalized")}>Finalize</button>
          </div>
        )}
        {error && <div className="error">{error}</div>}
      </div>

      <div className="card">
        <h3>Past notes</h3>
        {notes.length ? (
          notes.map((n) => (
            <div className="list-item" key={n.id}>
              <strong>{n.chief_complaint || "(no chief complaint)"}</strong>{" "}
              <span className={`badge ${n.status === "finalized" ? "ok" : ""}`}>{n.status}</span>
              <div className="muted">{n.created_at}</div>
            </div>
          ))
        ) : (
          <p className="muted">No notes yet.</p>
        )}
      </div>
    </>
  );
}
