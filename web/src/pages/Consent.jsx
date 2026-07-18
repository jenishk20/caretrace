import { useEffect, useState } from "react";
import { api } from "../api";
import { useApp } from "../context/AppContext";
import RecordButton from "../components/RecordButton";

export default function Consent() {
  const { staff, patientId } = useApp();
  const [forms, setForms] = useState([]);
  const [activeForm, setActiveForm] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [questionText, setQuestionText] = useState("");
  const [qaError, setQaError] = useState("");

  async function loadForms() {
    const list = await api.listConsentForms(patientId);
    setForms(list);
    return list;
  }

  useEffect(() => {
    loadForms().then((list) => {
      if (list.length) showForm(list[0].id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId]);

  async function showForm(formId) {
    const form = await api.getConsentForm(formId);
    setActiveForm(form);
  }

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploadStatus("Reading form and generating explanation (may take up to a minute)...");
    setUploadError("");
    try {
      const form = await api.createConsentForm(file, patientId, staff.id);
      setUploadStatus("");
      await loadForms();
      await showForm(form.id);
    } catch (err) {
      setUploadStatus("");
      setUploadError(err.message);
    }
  }

  async function ask(text, audioBlob) {
    setQaError("");
    try {
      const qa = await api.askConsentQuestion(activeForm.id, patientId, { questionText: text, audioBlob });
      setActiveForm((f) => ({ ...f, qa_log: [...(f.qa_log || []), qa] }));
      setQuestionText("");
    } catch (err) {
      setQaError(err.message);
    }
  }

  return (
    <>
      <div className="card">
        <h2>Consent Explainer</h2>
        <label>Photograph or upload the consent form</label>
        <input type="file" accept="image/*" capture="environment" onChange={handleUpload} />
        <div className="muted">{uploadStatus}</div>
        {uploadError && <div className="error">{uploadError}</div>}
      </div>

      {activeForm && (
        <>
          <div className="card">
            <h3>Plain-language explanation</h3>
            <p>{activeForm.plain_language_explanation}</p>
            <details>
              <summary className="muted">Show raw form text</summary>
              <pre>{activeForm.ocr_text}</pre>
            </details>
            <div>
              {(activeForm.suggested_questions || []).map((q, i) => (
                <span key={i} className="chip" onClick={() => setQuestionText(q)}>
                  {q}
                </span>
              ))}
            </div>
          </div>

          <div className="card">
            <h3>Ask a question</h3>
            <input
              placeholder="Type a question, or use a suggestion above"
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
              {(activeForm.qa_log || []).map((qa, i) => (
                <div className="qa-entry" key={i}>
                  <div className="q">Q: {qa.question_text}</div>
                  <div className="a">A: {qa.answer_text}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      <div className="card">
        <h3>Past forms for this patient</h3>
        {forms.length ? (
          forms.map((f) => (
            <div className="list-item" key={f.id}>
              <button onClick={() => showForm(f.id)}>
                Form #{f.id} — {f.created_at}
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
