import { useEffect, useState } from "react";
import { api } from "../api";

const SAMPLE = `INFORMED CONSENT FOR CARDIAC CATHETERIZATION

Procedure: Cardiac catheterization with possible coronary angioplasty and stent placement.
Purpose: To locate and treat narrowed or blocked coronary arteries causing your chest pain.
The procedure is performed under local anesthesia with sedation; you will be awake but relaxed.

Risks may include: bleeding or bruising at the catheter site, allergic reaction to contrast dye,
irregular heartbeat, and — rarely — heart attack, stroke, or damage to a blood vessel.

Alternatives: medication management, or coronary bypass surgery.

By signing, you confirm the procedure and its risks were explained and your questions answered.`;

const SPEECH_LOCALE = { en: "en-US", es: "es-ES", zh: "zh-CN", fr: "fr-FR", hi: "hi-IN", ar: "ar-SA", pt: "pt-PT", vi: "vi-VN" };

function speak(text, language) {
  try {
    if (!text || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = SPEECH_LOCALE[language] || "en-US";
    utterance.rate = 0.95;
    const code = utterance.lang.slice(0, 2).toLowerCase();
    const voice = window.speechSynthesis.getVoices().find((item) => item.lang?.toLowerCase().startsWith(code));
    if (voice) utterance.voice = voice;
    window.speechSynthesis.speak(utterance);
  } catch { /* Browser speech is an optional local convenience. */ }
}

export default function ConsentView({ pid, staff, patient }) {
  const [doc, setDoc] = useState(null);
  const [ocr, setOcr] = useState(SAMPLE);
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState("");
  const [qa, setQa] = useState([]);
  const [asking, setAsking] = useState(false);
  const language = patient?.primary_language || "en";
  const languageLabel = language === "es" ? "Español" : language;

  useEffect(() => {
    api.consentList(pid).then((forms) => {
      if (forms[0]) { setDoc(forms[0]); api.consentQuestions(forms[0].id, pid).then(setQa); }
    }).catch(() => {});
  }, [pid]);

  async function ingest() {
    setBusy(true);
    try {
      const d = await api.consentText({ patient_id: pid, staff_id: staff?.staff_id, ocr_text: ocr });
      setDoc(d);
      setQa([]);
      speak(d.explanation, language);
    } catch (e) { alert(e.message); } finally { setBusy(false); }
  }

  async function uploadImg(file) {
    setBusy(true);
    try {
      const d = await api.consentImage(pid, staff?.staff_id, file);
      setDoc(null); setOcr(d.ocr_text || ""); setQa([]);
    } catch (e) { alert(e.message); } finally { setBusy(false); }
  }

  async function ask(question) {
    const text = question ?? q;
    if (!text.trim() || !doc) return;
    setAsking(true);
    try {
      const res = await api.consentAsk(doc.id, pid, text);
      setQa((prev) => [...prev, { question: res.question, answer: res.answer }]);
      setQ("");
      speak(res.answer, language);
    } catch (e) { alert(e.message); } finally { setAsking(false); }
  }

  return (
    <div>
      <div className="muted" style={{ fontSize: 13 }}>Consent Explainer · Hear</div>
      <h1 style={{ fontSize: 26, letterSpacing: "-0.02em", marginBottom: 4 }}>Explain the consent form</h1>
      <p className="muted" style={{ marginBottom: 20 }}>
        MedSignal reads the form, explains it in plain language, and logs the patient's questions — real
        evidence they understood, not just a signature.
      </p>
      <div className="soft-note" style={{ marginTop: -8, marginBottom: 20, fontSize: 13 }}>
        🌐 Uses the patient portal language: <b>{languageLabel}</b>.
        Consent explanations and answers stay in that language.
      </div>

      <div className="two-col">
        <div className="card cn-form" style={{ padding: 18 }}>
          <div className="row between" style={{ marginBottom: 10 }}>
            <b style={{ fontSize: 14 }}>Form text</b>
            <label className="btn btn-ghost" style={{ padding: "6px 10px", fontSize: 12 }}>
              📷 Photo
              <input type="file" accept="image/png,image/jpeg,image/webp" style={{ display: "none" }}
                onChange={(e) => e.target.files[0] && uploadImg(e.target.files[0])} />
            </label>
          </div>
          <textarea className="textarea cn-text" style={{ fontFamily: "var(--mono)", fontSize: 12 }}
            value={ocr} onChange={(e) => setOcr(e.target.value)} />
          <button className="btn btn-primary" style={{ marginTop: 12, width: "100%", justifyContent: "center" }}
            onClick={ingest} disabled={busy}>
            {busy ? <span className="spinner" /> : "Explain this form"}
          </button>
        </div>

        <div className="col" style={{ gap: 16 }}>
          {doc && (
            <div className="card fade-up" style={{ padding: 18 }}>
              <div className="row" style={{ gap: 8, marginBottom: 10 }}>
                <span style={{ fontSize: 16 }}>◈</span><b>In plain language</b>
              </div>
              <div style={{ fontSize: 15, lineHeight: 1.6 }}>{doc.explanation}</div>
              <button className="chip" style={{ marginTop: 12 }} onClick={() => speak(doc.explanation, language)}>
                🔊 {language === "es" ? "Escuchar explicación" : "Read explanation aloud"}
              </button>
              {doc.suggested_questions?.length > 0 && (
                <>
                  <div className="sep" />
                  <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>QUESTIONS SHE MIGHT ASK</div>
                  <div className="row wrap" style={{ gap: 6 }}>
                    {doc.suggested_questions.map((sq, i) => (
                      <button key={i} className="chip" onClick={() => ask(sq)}>{sq}</button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {doc && (
            <div className="card" style={{ padding: 18 }}>
              <b style={{ fontSize: 14 }}>Patient Q&amp;A</b>
              <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>Grounded in the form. Every exchange is logged.</div>
              <div className="col" style={{ gap: 10, marginBottom: 12 }}>
                {qa.map((item, i) => (
                  <div key={i} className="fade-up">
                    <div className="qa-q">{item.question}</div>
                    <div className="qa-a">{item.answer}<button className="qa-speak" onClick={() => speak(item.answer, language)} title="Read aloud">🔊</button></div>
                  </div>
                ))}
              </div>
              <div className="row" style={{ gap: 8 }}>
                <input className="input" placeholder="Will I be awake?" value={q}
                  onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask()} />
                <button className="btn btn-primary" onClick={() => ask()} disabled={asking}>
                  {asking ? <span className="spinner" /> : "Ask"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        .two-col { display:grid; grid-template-columns:1fr 1fr; gap:16px; align-items:start; }
        /* A substantial form pane so the reading side has presence before an explanation exists. */
        .cn-form { min-height:440px; display:flex; flex-direction:column; }
        .cn-text { flex:1; min-height:300px; resize:vertical; }
        @media (max-width:960px){ .cn-form{min-height:0;} .cn-text{min-height:220px;} }
        .chip { font-size:12px; padding:6px 11px; border-radius:999px; background:var(--panel-2);
          border:1px solid var(--line); color:var(--text-dim); text-align:left; }
        .chip:hover { border-color:var(--teal-dim); color:var(--text); }
        .qa-q { font-weight:600; font-size:14px; }
        .qa-a { font-size:14px; color:var(--text-dim); margin-top:3px; padding-left:12px;
          border-left:2px solid var(--teal-dim); line-height:1.55; }
        .qa-speak { margin-left:8px; font-size:12px; opacity:0.65; vertical-align:middle; }
        .qa-speak:hover { opacity:1; }
        @media (max-width:960px){ .two-col{grid-template-columns:1fr;} }
      `}</style>
    </div>
  );
}
