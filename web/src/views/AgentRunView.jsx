import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import AgentReview from "../components/AgentReview.jsx";
import AgentWorkingPanel from "../components/AgentWorkingPanel.jsx";
import TracePanel from "../components/TracePanel.jsx";
import samplePrescription from "../assets/sample-prescription.svg";

const MODES = [
  { key: "speech", icon: "🎙", label: "Speak", hint: "Clinical round" },
  { key: "image", icon: "▣", label: "Photograph", hint: "Printed prescription" },
  { key: "text", icon: "⌨", label: "Type", hint: "Note or correction" },
];

export default function AgentRunView({ patient, pid, staff, refresh }) {
  const [mode, setMode] = useState("speech");
  const [text, setText] = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);
  const [error, setError] = useState("");
  const [bundle, setBundle] = useState(null);
  const [approvalBusy, setApprovalBusy] = useState(false);
  const [approvalResult, setApprovalResult] = useState(null);
  const [liveTrace, setLiveTrace] = useState([]);
  const recorderRef = useRef(null);
  const audioStreamRef = useRef(null);
  const videoRef = useRef(null);
  const cameraStreamRef = useRef(null);

  useEffect(() => () => {
    audioStreamRef.current?.getTracks().forEach((track) => track.stop());
    cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  function chooseMode(next) {
    setMode(next);
    setError("");
    setBundle(null);
    setLiveTrace([]);
    setApprovalResult(null);
  }

  async function toggleRecording() {
    if (recording) {
      recorderRef.current?.stop();
      setRecording(false);
      return;
    }
    try {
      setError("");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;
      const chunks = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => event.data.size && chunks.push(event.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        try {
          const result = await api.transcribe(new Blob(chunks, { type: recorder.mimeType || "audio/webm" }));
          setText(result.transcript || "");
        } catch (exc) { setError(exc.message); }
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch (exc) { setError(`Microphone unavailable: ${exc.message}`); }
  }

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } } });
      cameraStreamRef.current = stream;
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
      setCameraOn(true);
    } catch (exc) { setError(`Camera unavailable: ${exc.message}`); }
  }

  function captureCamera() {
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) return;
      const file = new File([blob], "prescription-camera.png", { type: "image/png" });
      selectImage(file);
      cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
      setCameraOn(false);
    }, "image/png");
  }

  function selectImage(file) {
    if (!file) return;
    setImageFile(file);
    setPreview(URL.createObjectURL(file));
    setError("");
  }

  async function useSample() {
    const svg = await fetch(samplePrescription).then((response) => response.blob());
    const url = URL.createObjectURL(svg);
    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = 1200;
      canvas.height = 760;
      canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => {
        URL.revokeObjectURL(url);
        if (blob) selectImage(new File([blob], "sample-ketorolac-prescription.png", { type: "image/png" }));
      }, "image/png");
    };
    image.src = url;
  }

  async function run() {
    setError("");
    setBusy(true);
    setBundle(null);
    setApprovalResult(null);
    try {
      const payload = { patient_id: pid, staff_id: staff?.staff_id, input_kind: mode, language: patient.primary_language || "en" };
      if (mode === "image") {
        if (!imageFile) throw new Error("Choose or capture a printed prescription first.");
        const upload = await api.uploadAgentImage(imageFile);
        payload.image_path = upload.path;
      } else {
        if (!text.trim()) throw new Error(mode === "speech" ? "Record or enter the spoken round first." : "Enter a note or correction first.");
        payload.text = text.trim();
      }
      const started = await api.startAgent(payload);
      const deadline = Date.now() + 8 * 60 * 1000;
      let completed = null;
      while (Date.now() < deadline) {
        await new Promise((resolve) => setTimeout(resolve, 700));
        const current = await api.agentRun(started.encounter_id);
        setLiveTrace(current.trace || []);
        if (current.status === "draft" || current.status === "approved" || current.status === "failed") {
          completed = current;
          break;
        }
      }
      if (!completed) throw new Error("The local agent timed out before completing the run.");
      if (completed.status === "failed") throw new Error("The local agent could not complete this run.");
      setBundle(completed.bundle);
      await refresh?.();
    } catch (exc) { setError(exc.message); } finally { setBusy(false); }
  }

  async function approve(approvals) {
    setApprovalBusy(true);
    setError("");
    try {
      const result = await api.approveAgent({ patient_id: pid, encounter_id: bundle.encounter_id, approvals });
      setApprovalResult(result);
      await refresh?.();
    } catch (exc) { setError(exc.message); } finally { setApprovalBusy(false); }
  }

  return (
    <div className="agent-run-view">
      <header className="agent-hero">
        <div><div className="eyebrow">One bedside input → complete workflow</div><h1>Run Confide for {patient.name}</h1><p>The local agent chooses the tools. Curated code verifies safety. You decide what leaves draft.</p></div>
        <div className="trust-lock"><span>●</span><b>ON-PREM</b><small>gpt-oss:20b</small></div>
      </header>
      <div className="mode-tabs">{MODES.map((item) => <button key={item.key} className={mode === item.key ? "on" : ""} onClick={() => chooseMode(item.key)}><span>{item.icon}</span><b>{item.label}</b><small>{item.hint}</small></button>)}</div>
      <div className="capture-grid">
        <section className="card capture-card">
          {mode === "speech" && <><h3>Capture the clinical round</h3><p className="muted">Whisper transcribes locally, then the agent fans the round out into drafts.</p><button className={`record-orb ${recording ? "recording" : ""}`} onClick={toggleRecording}><span>{recording ? "■" : "●"}</span>{recording ? "Stop recording" : "Record round"}</button><textarea className="textarea" value={text} onChange={(event) => setText(event.target.value)} placeholder="Transcript appears here. For a reliable demo, you can paste the round text too." /></>}
          {mode === "text" && <><h3>Type a note or correction</h3><p className="muted">Short corrections take a minimal tool path. Longer notes can trigger the complete workflow.</p><textarea className="textarea correction-input" value={text} onChange={(event) => setText(event.target.value)} placeholder='Try: "cancel the EKG"' autoFocus /></>}
          {mode === "image" && <><h3>Capture a printed prescription</h3><p className="muted">Tesseract reads the image locally before text reaches gpt-oss.</p><div className="image-actions"><label className="btn">Upload image<input hidden type="file" accept="image/*" capture="environment" onChange={(event) => selectImage(event.target.files?.[0])} /></label><button className="btn" onClick={cameraOn ? captureCamera : startCamera}>{cameraOn ? "Take snapshot" : "Open camera"}</button><button className="btn btn-ghost" onClick={useSample}>Use sample image</button></div><video ref={videoRef} className={cameraOn ? "camera visible" : "camera"} muted playsInline />{preview && <img className="rx-preview" src={preview} alt="Prescription selected for local OCR" />}</>}
          {error && <div className="capture-error">{error}</div>}
          <button className="btn btn-primary run-button" onClick={run} disabled={busy || recording}>{busy ? <><span className="spinner" /> Running local agent…</> : "Run →"}</button>
        </section>
        <AgentWorkingPanel busy={busy} inputKind={mode} trace={bundle?.trace || liveTrace} />
      </div>
      {bundle && <div className="results-stack fade-up"><AgentReview bundle={bundle} onApprove={approve} busy={approvalBusy} result={approvalResult} /><TracePanel trace={bundle.trace} /></div>}
      <style>{`
        .agent-run-view{display:grid;gap:18px}.agent-hero{display:flex;align-items:center;justify-content:space-between;gap:20px}.agent-hero h1{font-size:29px;letter-spacing:-.03em;margin:4px 0}.agent-hero p{color:var(--text-dim);max-width:720px}.trust-lock{padding:12px 14px;border:1px solid var(--teal-dim);border-radius:12px;display:grid;grid-template-columns:auto auto;gap:0 7px;color:var(--teal);min-width:140px}.trust-lock span{grid-row:1/3}.trust-lock small{color:var(--text-mute);font:10px var(--mono)}
        .mode-tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}.mode-tabs button{display:grid;grid-template-columns:30px 1fr;text-align:left;align-items:center;padding:12px 14px;background:var(--panel);border:1px solid var(--line);border-radius:12px;color:var(--text-dim)}.mode-tabs button>span{grid-row:1/3;font-size:20px}.mode-tabs button small{color:var(--text-mute)}.mode-tabs button.on{border-color:var(--teal);background:var(--panel-hi);box-shadow:0 0 0 3px var(--teal-glow);color:var(--text)}
        .capture-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:stretch}.capture-card{padding:20px}.capture-card h3{font-size:18px}.capture-card>.muted{font-size:13px;margin:4px 0 14px}.record-orb{width:100%;padding:16px;border:1px solid var(--teal-dim);border-radius:12px;background:rgba(47,230,200,.07);color:var(--teal);font-weight:800;margin-bottom:12px}.record-orb span{margin-right:8px}.record-orb.recording{color:var(--crit);border-color:var(--crit);animation:pulseCrit 1.2s infinite}.correction-input{min-height:150px}.run-button{width:100%;justify-content:center;margin-top:14px}.capture-error{padding:9px 11px;margin-top:10px;border-radius:8px;background:rgba(255,90,110,.1);color:var(--crit);font-size:12px}.image-actions{display:flex;gap:8px;flex-wrap:wrap}.camera{display:none}.camera.visible,.rx-preview{display:block;width:100%;max-height:280px;object-fit:contain;background:#fff;border-radius:10px;margin-top:12px}.results-stack{display:grid;gap:18px;margin-top:4px}
        @media(max-width:900px){.capture-grid{grid-template-columns:1fr}.agent-hero{align-items:start}.trust-lock{display:none}}@media(max-width:600px){.mode-tabs button{grid-template-columns:1fr;text-align:center}.mode-tabs button>span{grid-row:auto}.mode-tabs button small{display:none}}
      `}</style>
    </div>
  );
}
