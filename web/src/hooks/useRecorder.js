import { useCallback, useRef, useState } from "react";

// Record-then-submit audio capture (see SPEC.md's "record-then-submit" decision).
// Returns { recording, toggle } — toggle() starts on first call, stops (and fires
// onStop with the recorded Blob) on the next.
export function useRecorder(onStop) {
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  const toggle = useCallback(async () => {
    const current = mediaRecorderRef.current;
    if (current && current.state === "recording") {
      current.stop();
      return;
    }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      alert(`Microphone access failed: ${err.message}`);
      return;
    }
    streamRef.current = stream;
    chunksRef.current = [];
    const recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
    recorder.onstop = () => {
      streamRef.current.getTracks().forEach((t) => t.stop());
      setRecording(false);
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      onStop(blob);
    };
    mediaRecorderRef.current = recorder;
    recorder.start();
    setRecording(true);
  }, [onStop]);

  return { recording, toggle };
}
