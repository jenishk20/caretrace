import { useRecorder } from "../hooks/useRecorder";

export default function RecordButton({ onStop, idleLabel = "Record", recordingLabel = "Stop" }) {
  const { recording, toggle } = useRecorder(onStop);
  return (
    <button type="button" className={recording ? "recording" : ""} onClick={toggle}>
      {recording ? recordingLabel : idleLabel}
    </button>
  );
}
