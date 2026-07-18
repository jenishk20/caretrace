import { useEffect, useState } from "react";
import { api } from "../api";
import { useApp } from "../context/AppContext";
import RecordButton from "../components/RecordButton";

export default function Discharge() {
  const { staff, patientId } = useApp();
  const [docs, setDocs] = useState([]);
  const [activeDoc, setActiveDoc] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [questionText, setQuestionText] = useState("");
  const [qaError, setQaError] = useState("");
  const [reminders, setReminders] = useState([]);
  const [reminderDesc, setReminderDesc] = useState("");
  const [reminderTime, setReminderTime] = useState("");
  const [reminderError, setReminderError] = useState("");

  async function loadDocs() {
    const list = await api.listDischargeDocuments(patientId);
    setDocs(list);
    return list;
  }

  useEffect(() => {
    loadDocs().then((list) => {
      if (list.length) showDoc(list[0].id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId]);

  async function showDoc(docId) {
    const doc = await api.getDischargeDocument(docId);
    setActiveDoc(doc);
    await loadReminders();
  }

  async function loadReminders() {
    setReminders(await api.listReminders(patientId));
  }

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploadStatus("Reading discharge papers and extracting red flags (may take up to a minute)...");
    setUploadError("");
    try {
      const doc = await api.createDischargeDocument(file, patientId, staff.id);
      setUploadStatus("");
      await loadDocs();
      await showDoc(doc.id);
    } catch (err) {
      setUploadStatus("");
      setUploadError(err.message);
    }
  }

  async function ask(text, audioBlob) {
    setQaError("");
    try {
      const qa = await api.askDischargeQuestion(activeDoc.id, patientId, { questionText: text, audioBlob });
      setActiveDoc((d) => ({ ...d, qa_log: [...(d.qa_log || []), qa] }));
      setQuestionText("");
    } catch (err) {
      setQaError(err.message);
    }
  }

  async function addReminder() {
    setReminderError("");
    if (!reminderDesc.trim() || !reminderTime) {
      setReminderError("Description and date/time are required.");
      return;
    }
    try {
      await api.createReminder(activeDoc.id, reminderDesc.trim(), reminderTime);
      setReminderDesc("");
      setReminderTime("");
      await loadReminders();
    } catch (err) {
      setReminderError(err.message);
    }
  }

  async function markDone(id) {
    await api.updateReminder(id, { status: "done" });
    await loadReminders();
  }

  return (
    <>
      <div className="card">
        <h2>Discharge Navigator</h2>
        <label>Photograph or upload the discharge papers</label>
        <input type="file" accept="image/*" capture="environment" onChange={handleUpload} />
        <div className="muted">{uploadStatus}</div>
        {uploadError && <div className="error">{uploadError}</div>}
      </div>

      {activeDoc && (
        <>
          <div className="card">
            <h3>Red-flag symptoms</h3>
            {(activeDoc.red_flags || []).length ? (
              activeDoc.red_flags.map((rf, i) => (
                <div className="list-item" key={i}>
                  <strong>{rf.symptom}</strong>
                  <div className="muted">{rf.description}</div>
                </div>
              ))
            ) : (
              <p className="muted">None extracted from this document.</p>
            )}
            <details>
              <summary className="muted">Show raw document text</summary>
              <pre>{activeDoc.ocr_text}</pre>
            </details>
          </div>

          <div className="card">
            <h3>Ask a question</h3>
            <input
              placeholder="e.g. When can I shower?"
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
            />
            <RecordButton idleLabel="Record question" recordingLabel="Stop" onStop={(blob) => ask(null, blob)} />
            <button
              className="primary"
              onClick={() => {
                if (!questionText.trim()) {
                  setQaError("Type a question or record one.");
                  return;
                }
                ask(questionText.trim(), null);
              }}
            >
              Ask
            </button>
            {qaError && <div className="error">{qaError}</div>}
            <div style={{ marginTop: 16 }}>
              {(activeDoc.qa_log || []).map((qa, i) => (
                <div className="qa-entry" key={i}>
                  <div className="q">
                    Q: {qa.question_text}
                    {qa.is_red_flag && <span className="badge">RED FLAG</span>}
                  </div>
                  <div className="a">A: {qa.answer_text}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h3>Add a follow-up reminder</h3>
            <div className="row">
              <div>
                <label>Description</label>
                <input
                  placeholder="e.g. Follow-up appointment"
                  value={reminderDesc}
                  onChange={(e) => setReminderDesc(e.target.value)}
                />
              </div>
              <div>
                <label>Date/time</label>
                <input
                  type="datetime-local"
                  value={reminderTime}
                  onChange={(e) => setReminderTime(e.target.value)}
                />
              </div>
            </div>
            <button onClick={addReminder}>Add reminder</button>
            {reminderError && <div className="error">{reminderError}</div>}
            <div style={{ marginTop: 12 }}>
              {reminders.length ? (
                reminders.map((r) => (
                  <div className="list-item" key={r.id}>
                    {r.description} <span className="muted">— {r.remind_at}</span>{" "}
                    <span className={`badge ${r.status === "done" ? "ok" : ""}`}>{r.status}</span>
                    {r.status === "pending" && (
                      <button style={{ float: "right" }} onClick={() => markDone(r.id)}>
                        Mark done
                      </button>
                    )}
                  </div>
                ))
              ) : (
                <p className="muted">No reminders yet.</p>
              )}
            </div>
          </div>
        </>
      )}

      <div className="card">
        <h3>Past documents for this patient</h3>
        {docs.length ? (
          docs.map((d) => (
            <div className="list-item" key={d.id}>
              <button onClick={() => showDoc(d.id)}>
                Document #{d.id} — {d.created_at}
              </button>
            </div>
          ))
        ) : (
          <p className="muted">None yet.</p>
        )}
      </div>
    </>
  );
}
