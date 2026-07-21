import { useState } from "react";
import { api } from "../api";

export default function HandoffView({ pid, staff }) {
  const [handoff, setHandoff] = useState(null);
  const [busyH, setBusyH] = useState(false);
  const [brief, setBrief] = useState(null);
  const [busyB, setBusyB] = useState(false);

  async function generate() {
    setBusyH(true);
    try { setHandoff(await api.generateHandoff(pid, staff?.staff_id)); }
    catch (e) { alert(e.message); } finally { setBusyH(false); }
  }
  async function catchUp() {
    setBusyB(true);
    try { setBrief(await api.catchMeUp(pid)); }
    catch (e) { alert(e.message); } finally { setBusyB(false); }
  }

  return (
    <div>
      <div className="muted" style={{ fontSize: 13 }}>Handoff · Remember</div>
      <h1 style={{ fontSize: 26, letterSpacing: "-0.02em", marginBottom: 4 }}>Nothing dropped in the gap</h1>
      <p className="muted" style={{ marginBottom: 20 }}>
        The whole stay, written up from the graph — an SBAR handoff for the next shift, or a 15-second
        catch-up for a covering clinician.
      </p>

      <div className="two-col">
        <div className="card" style={{ padding: 20 }}>
          <div className="row between" style={{ marginBottom: 12 }}>
            <div className="row" style={{ gap: 8 }}><span style={{ fontSize: 16 }}>🔀</span><b>SBAR handoff</b></div>
            <button className="btn btn-primary" onClick={generate} disabled={busyH}>
              {busyH ? <span className="spinner" /> : "Generate"}
            </button>
          </div>
          {!handoff && <div className="muted" style={{ fontSize: 13 }}>Auto-written from the day's notes, leading with what's urgent.</div>}
          {handoff && (
            <div className="fade-up">
              {handoff.priority_note && (
                <div className="priority">
                  <span className="tag" style={{ background: "var(--crit-glow)", color: "var(--crit)" }}>Most urgent</span>
                  <div style={{ marginTop: 6, fontWeight: 600 }}>{handoff.priority_note}</div>
                </div>
              )}
              <Sbar letter="S" label="Situation" text={handoff.situation} />
              <Sbar letter="B" label="Background" text={handoff.background} />
              <Sbar letter="A" label="Assessment" text={handoff.assessment} />
              <Sbar letter="R" label="Recommendation" text={handoff.recommendation} />
            </div>
          )}
        </div>

        <div className="card" style={{ padding: 20 }}>
          <div className="row between" style={{ marginBottom: 12 }}>
            <div className="row" style={{ gap: 8 }}><span style={{ fontSize: 16 }}>⏱</span><b>"Catch me up"</b></div>
            <button className="btn btn-primary" onClick={catchUp} disabled={busyB}>
              {busyB ? <span className="spinner" /> : "Brief me"}
            </button>
          </div>
          {!brief && <div className="muted" style={{ fontSize: 13 }}>A covering clinician who's never met the patient gets the whole stay in ~15 seconds.</div>}
          {brief && (
            <div className="fade-up">
              <div className="brief">
                <span style={{ color: "var(--teal)", fontSize: 12, fontWeight: 700 }}>◈ CONFIDE</span>
                <div style={{ marginTop: 6, fontSize: 15, lineHeight: 1.6 }}>{brief.briefing}</div>
              </div>
              {brief.open_alerts?.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>OPEN GUARDIAN CONCERNS</div>
                  {brief.open_alerts.map((a) => (
                    <div key={a.id} className="mini-alert">⚠ {a.title}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <style>{`
        .two-col { display:grid; grid-template-columns:1fr 1fr; gap:16px; align-items:start; }
        .priority { background:rgba(255,90,110,0.08); border:1px solid rgba(255,90,110,0.35);
          border-radius:10px; padding:12px 14px; margin-bottom:14px; }
        .sbar { display:flex; gap:12px; padding:12px 0; border-top:1px solid var(--line-soft); }
        .sbar-letter { width:28px; height:28px; border-radius:8px; background:var(--panel-hi); color:var(--teal);
          display:grid; place-items:center; font-weight:800; flex-shrink:0; }
        .brief { background:rgba(47,230,200,0.06); border:1px solid var(--teal-dim); border-radius:10px; padding:14px 16px; }
        .mini-alert { font-size:13px; color:var(--warn); padding:6px 10px; background:var(--bg-soft);
          border:1px solid var(--line-soft); border-radius:8px; margin-bottom:6px; }
        @media (max-width:960px){ .two-col{grid-template-columns:1fr;} }
      `}</style>
    </div>
  );
}

function Sbar({ letter, label, text }) {
  return (
    <div className="sbar">
      <div className="sbar-letter">{letter}</div>
      <div>
        <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
        <div style={{ fontSize: 14, marginTop: 2, lineHeight: 1.5 }}>{text || "—"}</div>
      </div>
    </div>
  );
}
