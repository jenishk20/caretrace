import { useEffect, useState } from "react";
import { api } from "../api";

const SAMPLE = `DISCHARGE INSTRUCTIONS — After Cardiac Catheterization

You had a cardiac catheterization. A small stent was placed to keep an artery open.

Activity: Rest today. No heavy lifting (over 10 lbs) or strenuous activity for 5 days.
You may shower after 24 hours, but do not soak the catheter site in a bath for 1 week.

Wound care: Keep the groin/wrist site clean and dry. A small bruise is normal.

Medications: Take aspirin 81 mg once daily. Take clopidogrel 75 mg once daily for 12 months.
Continue your warfarin as directed.

CALL 911 OR RETURN TO THE ER IF YOU HAVE:
- Chest pain or pressure that does not go away
- Bleeding from the catheter site that won't stop
- A leg or arm that becomes cold, blue, or numb
- Fever over 101°F, or shortness of breath

Follow-up: See your cardiologist in 1 week.`;

export default function DischargeView({ pid, staff }) {
  const [doc, setDoc] = useState(null);
  const [ocr, setOcr] = useState(SAMPLE);
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState("");
  const [qa, setQa] = useState([]);
  const [asking, setAsking] = useState(false);
  const [reminders, setReminders] = useState([]);

  const loadReminders = () => api.reminders(pid).then(setReminders).catch(() => {});
  useEffect(() => {
    api.dischargeList(pid).then((docs) => docs[0] && setDoc(docs[0])).catch(() => {});
    loadReminders();
  }, [pid]);

  async function ingest() {
    setBusy(true);
    try {
      const d = await api.dischargeText({ patient_id: pid, staff_id: staff?.staff_id, ocr_text: ocr });
      setDoc(d); setQa([]); loadReminders();
    } catch (e) { alert(e.message); } finally { setBusy(false); }
  }

  async function uploadImg(file) {
    setBusy(true);
    try {
      const d = await api.dischargeImage(pid, staff?.staff_id, file);
      setDoc(null); setOcr(d.ocr_text || ""); setQa([]);
    } catch (e) { alert(e.message); } finally { setBusy(false); }
  }

  async function ask(question) {
    const text = question ?? q;
    if (!text.trim() || !doc) return;
    setAsking(true);
    try {
      const res = await api.dischargeAsk(doc.id, pid, text);
      setQa((prev) => [...prev, res]);
      setQ("");
    } catch (e) { alert(e.message); } finally { setAsking(false); }
  }

  return (
    <div>
      <div className="muted" style={{ fontSize: 13 }}>Discharge Navigator · Hear + Watch</div>
      <h1 style={{ fontSize: 26, letterSpacing: "-0.02em", marginBottom: 4 }}>The going-home plan</h1>
      <p className="muted" style={{ marginBottom: 20 }}>
        MedSignal explains the discharge sheet, pulls out the red-flag symptoms, and checks anything the
        patient mentions against them — flagging what's urgent.
      </p>

      <div className="two-col">
        <div className="card" style={{ padding: 18 }}>
          <div className="row between">
            <b style={{ fontSize: 14 }}>Discharge sheet</b>
            <label className="btn btn-ghost" style={{ padding: "6px 10px", fontSize: 12 }}>
              📷 Photo
              <input type="file" accept="image/png,image/jpeg,image/webp" style={{ display: "none" }}
                onChange={(e) => e.target.files[0] && uploadImg(e.target.files[0])} />
            </label>
          </div>
          <textarea className="textarea" style={{ minHeight: 240, marginTop: 10, fontFamily: "var(--mono)", fontSize: 12 }}
            value={ocr} onChange={(e) => setOcr(e.target.value)} />
          <button className="btn btn-primary" style={{ marginTop: 12, width: "100%", justifyContent: "center" }}
            onClick={ingest} disabled={busy}>
            {busy ? <span className="spinner" /> : "Explain & extract red flags"}
          </button>
        </div>

        <div className="col" style={{ gap: 16 }}>
          {doc && (
            <>
              <div className="card fade-up" style={{ padding: 18 }}>
                <div className="row" style={{ gap: 8, marginBottom: 10 }}>
                  <span style={{ fontSize: 16 }}>◈</span><b>In plain language</b>
                </div>
                <div style={{ fontSize: 15, lineHeight: 1.6 }}>{doc.explanation}</div>
              </div>

              {doc.red_flags?.length > 0 && (
                <div className="card" style={{ padding: 18, borderColor: "var(--crit)" }}>
                  <div className="row" style={{ gap: 8, marginBottom: 10 }}>
                    <span style={{ fontSize: 16 }}>🚩</span><b>Red-flag symptoms — go to the ER</b>
                  </div>
                  <div className="col" style={{ gap: 8 }}>
                    {doc.red_flags.map((rf, i) => (
                      <div key={i} className="redflag">
                        <b style={{ fontSize: 13 }}>{rf.symptom}</b>
                        <div className="muted" style={{ fontSize: 12 }}>{rf.description}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="card" style={{ padding: 18 }}>
                <b style={{ fontSize: 14 }}>Ask about going home</b>
                <div className="muted" style={{ fontSize: 12, marginBottom: 10 }}>Grounded in the sheet. Symptoms are matched to the red-flag list.</div>
                <div className="col" style={{ gap: 10, marginBottom: 12 }}>
                  {qa.map((item, i) => (
                    <div key={i} className="fade-up">
                      <div className="qa-q">{item.question}</div>
                      <div className={`qa-a ${item.is_red_flag ? "danger" : ""}`}>
                        {item.is_red_flag && <span className="tag" style={{ background: "var(--crit-glow)", color: "var(--crit)", marginRight: 6 }}>URGENT</span>}
                        {item.answer}
                        {item.urgency && <div style={{ color: "var(--crit)", fontWeight: 600, marginTop: 4 }}>{item.urgency}</div>}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="row wrap" style={{ gap: 6, marginBottom: 10 }}>
                  {["When can I shower?", "I have chest pain that won't go away", "What about my warfarin?"].map((sq) => (
                    <button key={sq} className="chip" onClick={() => ask(sq)}>{sq}</button>
                  ))}
                </div>
                <div className="row" style={{ gap: 8 }}>
                  <input className="input" placeholder="Ask a question…" value={q}
                    onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask()} />
                  <button className="btn btn-primary" onClick={() => ask()} disabled={asking}>
                    {asking ? <span className="spinner" /> : "Ask"}
                  </button>
                </div>
              </div>
            </>
          )}

          {reminders.length > 0 && (
            <div className="card" style={{ padding: 18 }}>
              <div className="row" style={{ gap: 8, marginBottom: 10 }}>
                <span style={{ fontSize: 16 }}>⏰</span><b>Reminders that leave with her</b>
              </div>
              <div className="col" style={{ gap: 8 }}>
                {reminders.map((r) => (
                  <div key={r.id} className="row between reminder">
                    <div>
                      <b style={{ fontSize: 13 }}>{r.description}</b>
                      {r.schedule_text && <span className="muted" style={{ fontSize: 12 }}> · {r.schedule_text}</span>}
                    </div>
                    <span className="pill" style={{ fontSize: 11 }}>{r.status}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        .two-col { display:grid; grid-template-columns:1fr 1fr; gap:16px; align-items:start; }
        .chip { font-size:12px; padding:6px 11px; border-radius:999px; background:var(--panel-2);
          border:1px solid var(--line); color:var(--text-dim); text-align:left; }
        .chip:hover { border-color:var(--teal-dim); color:var(--text); }
        .redflag { background:var(--bg-soft); border:1px solid rgba(255,90,110,0.3); border-radius:8px; padding:10px 12px; }
        .qa-q { font-weight:600; font-size:14px; }
        .qa-a { font-size:14px; color:var(--text-dim); margin-top:3px; padding-left:12px;
          border-left:2px solid var(--teal-dim); line-height:1.55; }
        .qa-a.danger { border-left-color:var(--crit); }
        .reminder { padding:10px 12px; background:var(--bg-soft); border:1px solid var(--line-soft); border-radius:8px; }
        @media (max-width:960px){ .two-col{grid-template-columns:1fr;} }
      `}</style>
    </div>
  );
}
