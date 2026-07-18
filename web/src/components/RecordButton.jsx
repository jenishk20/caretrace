import { useRef, useState } from "react";
import { api } from "../api";

// A capture control that records from the mic and transcribes locally, OR lets
// you type the text. Every "spoken" interaction has a typed fallback so a demo
// never hard-fails on audio.
export default function RecordButton({ onText, placeholder = "Type or dictate…", cta = "Capture" }) {
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
    <div className="col" style={{ gap: 10 }}>
      <textarea
        className="textarea"
        placeholder={placeholder}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="row between">
        <div className="row" style={{ gap: 8 }}>
          {recording ? (
            <button className="btn btn-danger" onClick={stopRec}>
              <span className="rec-dot" /> Stop &amp; transcribe
            </button>
          ) : (
            <button className="btn btn-ghost" onClick={startRec} disabled={busy}>
              {busy ? <span className="spinner" /> : "🎙"} {busy ? "Transcribing…" : "Dictate"}
            </button>
          )}
        </div>
        <button className="btn btn-primary" onClick={submit} disabled={!text.trim()}>
          {cta}
        </button>
      </div>
      <style>{`
        .rec-dot { width:9px;height:9px;border-radius:50%;background:var(--crit);
          box-shadow:0 0 0 0 var(--crit-glow); animation:pulseCrit 1s infinite; display:inline-block; }
      `}</style>
    </div>
  );
}
