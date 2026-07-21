import { useRef, useState } from "react";
import { api } from "../api";

// A capture control that records from the mic and transcribes locally, OR lets
// you type the text. Every "spoken" interaction has a typed fallback so a demo
// never hard-fails on audio.
export default function RecordButton({ onText, placeholder = "Type or dictate…", cta = "Capture", grow = false }) {
  const [mode, setMode] = useState("text");
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState("");
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);

  async function startRec() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => chunksRef.current.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setBusy(true);
        try {
          const blob = new Blob(chunksRef.current, { type: "audio/webm" });
          const { transcript } = await api.transcribe(blob);
          setText((t) => (t ? t + " " : "") + transcript);
        } catch (e) {
          alert("Transcription unavailable — type instead. (" + e.message + ")");
        } finally {
          setBusy(false);
        }
      };
      mr.start();
      mediaRef.current = mr;
      setRecording(true);
    } catch {
      alert("Microphone not available — type instead.");
      setMode("text");
    }
  }

  function stopRec() {
    mediaRef.current?.stop();
    setRecording(false);
  }

  function submit() {
    if (!text.trim()) return;
    onText(text.trim());
    setText("");
  }

  return (
    <div className={`rb ${grow ? "rb-grow" : ""}`}>
      <div className={`rb-field ${recording ? "recording" : ""}`}>
        <textarea
          className="rb-textarea"
          placeholder={placeholder}
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
        />
        {recording && (
          <div className="rb-live">
            <span className="rec-dot" /> Listening… speak now
          </div>
        )}
        {busy && (
          <div className="rb-live">
            <span className="spinner" /> Transcribing on-device…
          </div>
        )}
      </div>
      <div className="rb-actions">
        {recording ? (
          <button className="btn btn-danger" onClick={stopRec}>
            <span className="rec-dot" /> Stop &amp; transcribe
          </button>
        ) : (
          <button className="btn btn-ghost" onClick={startRec} disabled={busy}>
            {busy ? <span className="spinner" /> : "🎙"} {busy ? "Transcribing…" : "Dictate"}
          </button>
        )}
        <button className="btn btn-primary" onClick={submit} disabled={!text.trim() || busy}>
          {cta}
        </button>
      </div>
      <style>{`
        .rb { display:flex; flex-direction:column; gap:12px; }
        .rb-grow { height:100%; }
        .rb-grow .rb-field { flex:1; display:flex; flex-direction:column; }
        .rb-grow .rb-textarea { flex:1; resize:none; }
        .rb-field { position:relative; border:1px solid var(--line); border-radius:12px;
          background:var(--panel-2); transition:border-color 0.2s, box-shadow 0.2s; }
        .rb-field:focus-within { border-color:var(--teal-dim); box-shadow:0 0 0 3px var(--teal-glow); }
        .rb-field.recording { border-color:var(--crit); box-shadow:0 0 0 3px var(--crit-glow); }
        .rb-textarea { width:100%; box-sizing:border-box; resize:vertical; min-height:104px;
          background:transparent; border:0; outline:none; color:var(--text); font:inherit;
          padding:14px 15px; line-height:1.55; }
        .rb-textarea::placeholder { color:var(--text-mute); }
        .rb-live { display:flex; align-items:center; gap:8px; font-size:12px; color:var(--text-dim);
          padding:0 15px 12px; }
        .rb-actions { display:flex; align-items:center; justify-content:space-between; gap:8px; }
        .rec-dot { width:9px;height:9px;border-radius:50%;background:var(--crit);
          box-shadow:0 0 0 0 var(--crit-glow); animation:pulseCrit 1s infinite; display:inline-block; }
      `}</style>
    </div>
  );
}
