import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { session } from "../lib/session.js";
import NetworkPill from "../components/NetworkPill.jsx";
import LocalModelConsole from "../components/LocalModelConsole.jsx";

// The patient's own space — everything about their care, in their language, entirely on
// their side and on-device. Three tabs: Home (orientation + ask-anything), My medicines
// (what each is for + a camera that checks a new medicine against their record), and My
// journey (the timeline of their stay). The language selector drives all of it.

const LANGS = [
  { code: "en", label: "English", flag: "🇬🇧" },
  { code: "es", label: "Español", flag: "🇪🇸" },
  { code: "zh", label: "中文", flag: "🇨🇳" },
  { code: "fr", label: "Français", flag: "🇫🇷" },
  { code: "hi", label: "हिन्दी", flag: "🇮🇳" },
  { code: "ar", label: "العربية", flag: "🇸🇦" },
  { code: "pt", label: "Português", flag: "🇵🇹" },
  { code: "vi", label: "Tiếng Việt", flag: "🇻🇳" },
];
const BCP = { en: "en-US", es: "es-ES", zh: "zh-CN", fr: "fr-FR", hi: "hi-IN", ar: "ar-SA", pt: "pt-PT", vi: "vi-VN" };
const CHAT_COPY = {
  en: {
    title: "MedSignal is with you",
    subtitle: "Calm, plain answers in your language — on this device.",
    greeting: (name) => `Hi ${name}. Ask me anything about your care — I'll answer in your language.`,
    suggestions: ["What's happening to me?", "Why am I here?", "What are my medications for?", "Is it serious?"],
    placeholder: "Ask me anything…",
    send: "Send",
  },
  es: {
    title: "MedSignal está contigo",
    subtitle: "Respuestas claras y tranquilas en tu idioma — en este dispositivo.",
    greeting: (name) => `Hola ${name}. Pregúntame lo que quieras sobre tu atención; te responderé en español.`,
    suggestions: ["¿Qué me está pasando?", "¿Por qué estoy aquí?", "¿Para qué son mis medicamentos?", "¿Es grave?"],
    placeholder: "Pregúntame lo que quieras…",
    send: "Enviar",
  },
};

function speak(text, lang) {
  try {
    const synth = window.speechSynthesis;
    if (!synth || !text) return;
    synth.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = BCP[lang] || "en-US";
    u.rate = 0.95;
    // Prefer a voice that matches the language so it actually reads it back.
    const pref = (BCP[lang] || "en").slice(0, 2).toLowerCase();
    const voice = synth.getVoices().find((v) => v.lang?.toLowerCase().startsWith(pref));
    if (voice) u.voice = voice;
    synth.speak(u);
  } catch { /* noop */ }
}

const TABS = [
  { key: "home", icon: "💙", label: "Home" },
  { key: "meds", icon: "💊", label: "My medicines" },
  { key: "journey", icon: "🗺", label: "My journey" },
];

export default function PatientHome() {
  const nav = useNavigate();
  const me = session.patient();
  const pid = me?.patient_id;
  const [lang, setLang] = useState(me?.primary_language || "en");
  const [tab, setTab] = useState("home");

  // Fast record data loads on entry. Model-written translations wait for the patient to
  // open that section, so a chat question is never held behind background model work.
  const [day, setDay] = useState(null);
  const [dayBusy, setDayBusy] = useState(false);
  const [meds, setMeds] = useState(null);
  const [reminders, setReminders] = useState([]);
  const [journey, setJourney] = useState(null);

  const loadDay = useCallback(async () => {
    if (!pid) return;
    setDayBusy(true);
    try { setDay(await api.orient(pid, null, lang)); }
    catch { /* noop */ } finally { setDayBusy(false); }
  }, [pid, lang]);

  const loadMeds = useCallback(() => {
    if (!pid) return;
    setMeds(null);
    api.patientMedications(pid, lang).then((r) => setMeds(r.medications)).catch(() => setMeds([]));
    api.patientReminders(pid).then(setReminders).catch(() => {});
  }, [pid, lang]);

  const loadMedPurposes = useCallback(() => {
    if (!pid) return;
    api.patientMedPurposes(pid, lang).then((pr) => {
      setMeds((cur) => (cur || []).map((m) => ({ ...m, purpose: pr.purposes[m.name.toLowerCase()] || m.purpose })));
    }).catch(() => {});
  }, [pid, lang]);

  const loadJourney = useCallback(() => {
    if (!pid) return;
    setJourney(null);
    api.patientJourney(pid, lang, false).then(setJourney).catch(() => setJourney({ visits: [] }));
  }, [pid, lang]);

  const loadJourneyTranslation = useCallback(() => {
    if (!pid) return;
    api.patientJourney(pid, lang, true).then(setJourney).catch(() => {});
  }, [pid, lang]);

  useEffect(() => { loadMeds(); loadJourney(); }, [loadMeds, loadJourney]);
  useEffect(() => {
    if (tab === "meds") loadMedPurposes();
    if (tab === "journey") loadJourneyTranslation();
  }, [tab, loadMedPurposes, loadJourneyTranslation]);

  function logout() { session.clearPatient(); nav("/"); }

  async function changeLang(code) {
    setLang(code);
    try { await api.setPatientLanguage(pid, code); } catch { /* noop */ }
  }

  if (!me) { nav("/patient/login"); return null; }

  return (
    <div className="ph">
      <div className="ph-top">
        <div className="row" style={{ gap: 10 }}>
          <span style={{ color: "var(--teal)", fontSize: 20 }}>◈</span>
          <b>MedSignal</b>
          <span className="muted" style={{ fontSize: 13 }}>· {me.name?.split(" ")[0]}</span>
        </div>
        <div className="row" style={{ gap: 12 }}>
          <select className="lang-sel" value={lang} onChange={(e) => changeLang(e.target.value)}>
            {LANGS.map((l) => <option key={l.code} value={l.code}>{l.flag} {l.label}</option>)}
          </select>
          <NetworkPill />
          <button className="btn btn-ghost" style={{ padding: "7px 12px" }} onClick={logout}>Sign out</button>
        </div>
      </div>

      <div className="ph-tabs">
        {TABS.map((t) => (
          <button key={t.key} className={`ph-tab ${tab === t.key ? "on" : ""}`} onClick={() => setTab(t.key)}>
            <span style={{ fontSize: 16 }}>{t.icon}</span> {t.label}
          </button>
        ))}
      </div>

      <div className="ph-body">
        {tab === "home" && <HomeTab me={me} lang={lang} day={day} dayBusy={dayBusy} loadDay={loadDay} />}
        {tab === "meds" && <MedsTab me={me} lang={lang} meds={meds} reminders={reminders} />}
        {tab === "journey" && <JourneyTab me={me} lang={lang} journey={journey} />}
      </div>

      <LocalModelConsole />

      <style>{`
        .ph { min-height:100vh; }
        .ph-top { display:flex; justify-content:space-between; align-items:center; padding:16px 28px;
          border-bottom:1px solid var(--line); position:sticky; top:0; background:rgba(10,14,26,0.7);
          backdrop-filter:blur(10px); z-index:10; }
        .lang-sel { background:var(--panel-2); border:1px solid var(--line); color:var(--text);
          border-radius:999px; padding:7px 12px; font-size:13px; }
        .ph-tabs { display:flex; gap:8px; justify-content:center; padding:16px; }
        .ph-tab { display:flex; align-items:center; gap:8px; padding:9px 18px; border-radius:999px;
          background:var(--panel); border:1px solid var(--line); color:var(--text-dim); font-weight:600; font-size:14px; }
        .ph-tab.on { background:var(--panel-hi); color:var(--text); border-color:var(--teal-dim); }
        .ph-body { max-width:1040px; margin:0 auto; padding:8px 26px 40px; }
        .soft-note { margin-top:12px; background:rgba(47,230,200,0.06); border:1px solid var(--teal-dim);
          border-radius:10px; padding:12px 14px; font-size:15px; line-height:1.6; }
        .chip { font-size:13px; padding:8px 13px; border-radius:999px; background:var(--panel-2);
          border:1px solid var(--line); color:var(--text-dim); }
        .chip:hover { border-color:var(--teal-dim); color:var(--text); }
      `}</style>
    </div>
  );
}

// --- HOME: orientation + ask-anything ---------------------------------------
function HomeTab({ me, lang, day, dayBusy, loadDay }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [debrief, setDebrief] = useState(null);
  const scrollRef = useRef(null);
  const copy = CHAT_COPY[lang] || CHAT_COPY.en;

  useEffect(() => { setMessages([]); }, [lang]);
  useEffect(() => { scrollRef.current?.scrollTo({ top: 9e9, behavior: "smooth" }); }, [messages]);
  async function getDebrief() {
    setBusy(true);
    try { const r = await api.patientDebrief(me.patient_id, lang); setDebrief(r.debrief); speak(r.debrief, lang); }
    catch (e) { alert(e.message); } finally { setBusy(false); }
  }
  async function send(text) {
    const msg = text ?? input;
    if (!msg.trim()) return;
    // User bubble + an empty MedSignal bubble that streams tokens as they arrive.
    setMessages((m) => [...m, { from: "me", text: msg }, { from: "assistant", text: "" }]);
    setInput(""); setBusy(true);
    const fill = (t) => setMessages((m) => {
      const c = [...m]; c[c.length - 1] = { from: "assistant", text: t }; return c;
    });
    try {
      const full = await api.patientChatStream(me.patient_id, msg, fill, lang);
      speak(full, lang);
    } catch {
      fill("I'm having trouble — please ask your nurse.");
    } finally { setBusy(false); }
  }

  return (
    <div className="home-grid">
      <div className="ph-chat card">
        <div className="ph-chat-head">
          <div className="orb" />
          <div>
            <b>{copy.title}</b>
            <div className="muted" style={{ fontSize: 12 }}>{copy.subtitle}</div>
          </div>
        </div>
        <div className="ph-messages" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="bubble assistant">{copy.greeting(me.name?.split(" ")[0])}</div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`bubble ${m.from}`}>
              {m.from === "assistant" && !m.text ? (
                <span className="typing"><i /><i /><i /></span>
              ) : (
                <>
                  {m.text}
                  {m.from === "assistant" && (
                    <button className="bubble-speak" onClick={() => speak(m.text, lang)} title="Read aloud">🔊</button>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
        <div className="ph-suggest">
          {copy.suggestions.map((s) => <button key={s} className="chip" onClick={() => send(s)} disabled={busy}>{s}</button>)}
        </div>
        <div className="ph-input">
          <input className="input" placeholder={copy.placeholder} value={input}
            onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} />
          <button className="btn btn-primary" onClick={() => send()} disabled={busy}>{copy.send}</button>
        </div>
      </div>

      <div className="col" style={{ gap: 16 }}>
        <div className="card" style={{ padding: 18 }}>
          <div className="row between" style={{ marginBottom: 10 }}>
            <div className="row" style={{ gap: 8 }}><span style={{ fontSize: 16 }}>📋</span><b>My day today</b></div>
            {day && <button className="chip" onClick={loadDay} disabled={dayBusy}>{dayBusy ? "…" : "↻"}</button>}
          </div>
          {!day && dayBusy && <span className="spinner" />}
          {!day && !dayBusy && (
            <button className="btn" style={{ width: "100%", justifyContent: "center" }} onClick={loadDay}>See my day</button>
          )}
          {day && (
            <div className="fade-up">
              <div style={{ fontWeight: 700, fontSize: 15 }}>{day.date_line}</div>
              {day.status_line && <div className="dim" style={{ fontSize: 14, marginTop: 3, lineHeight: 1.5 }}>{day.status_line}</div>}
              {day.checklist?.length > 0 && (
                <div className="today-list">
                  {day.checklist.map((it, i) => (
                    <div key={i} className="today-item"><span className="tick">☐</span><span>{it}</span></div>
                  ))}
                </div>
              )}
              <button className="chip" style={{ marginTop: 10 }} onClick={() => speak(day.script_text, lang)}>🔊 Read aloud</button>
            </div>
          )}
        </div>
        <div className="card" style={{ padding: 18 }}>
          <div className="row" style={{ gap: 8, marginBottom: 8 }}><span style={{ fontSize: 16 }}>📋</span><b>Recap my visit</b></div>
          <p className="muted" style={{ fontSize: 13, marginBottom: 12 }}>One plain-language summary of your whole stay.</p>
          <button className="btn" style={{ width: "100%", justifyContent: "center" }} onClick={getDebrief} disabled={busy}>Give me the recap</button>
          {debrief && <div className="soft-note fade-up">{debrief}</div>}
        </div>
      </div>

      <style>{`
        .home-grid { display:grid; grid-template-columns:1.5fr 1fr; gap:16px; align-items:start; }
        .ph-chat { display:flex; flex-direction:column; height:68vh; }
        .ph-chat-head { display:flex; gap:12px; align-items:center; padding:16px 18px; border-bottom:1px solid var(--line); }
        .orb { width:34px; height:34px; border-radius:50%; background:radial-gradient(circle at 35% 30%, #6ffbe4, var(--teal-dim));
          box-shadow:0 0 18px var(--teal-glow); animation:breathe 3s ease-in-out infinite; }
        @keyframes breathe { 0%,100%{transform:scale(1);opacity:0.9;} 50%{transform:scale(1.08);opacity:1;} }
        .ph-messages { flex:1; overflow-y:auto; padding:18px; display:flex; flex-direction:column; gap:10px; }
        .bubble { max-width:82%; padding:12px 15px; border-radius:16px; font-size:15px; line-height:1.55; animation:fadeUp 0.3s ease both; }
        .bubble.me { align-self:flex-end; background:var(--panel-hi); border:1px solid var(--line); border-bottom-right-radius:4px; }
        .bubble.assistant { align-self:flex-start; background:linear-gradient(180deg,rgba(47,230,200,0.1),rgba(47,230,200,0.04));
          border:1px solid var(--teal-dim); border-bottom-left-radius:4px; }
        .typing { display:inline-flex; gap:4px; }
        .typing i { width:7px; height:7px; border-radius:50%; background:var(--teal); animation:blink 1.2s infinite; }
        .typing i:nth-child(2){animation-delay:0.2s;} .typing i:nth-child(3){animation-delay:0.4s;}
        @keyframes blink { 0%,60%,100%{opacity:0.3;} 30%{opacity:1;} }
        .ph-suggest { display:flex; flex-wrap:wrap; gap:6px; padding:0 18px 12px; }
        .ph-input { display:flex; gap:8px; padding:14px 18px; border-top:1px solid var(--line); }
        .bubble-speak { margin-left:8px; font-size:12px; opacity:0.55; vertical-align:middle; }
        .bubble-speak:hover { opacity:1; }
        .today-list { margin-top:12px; display:flex; flex-direction:column; gap:8px; }
        .today-item { display:flex; gap:10px; align-items:flex-start; font-size:14px; padding:9px 11px;
          background:var(--bg-soft); border:1px solid var(--line-soft); border-radius:8px; line-height:1.45; }
        .tick { color:var(--teal); font-size:15px; }
        @media (max-width:900px){ .home-grid{grid-template-columns:1fr;} .ph-chat{height:56vh;} }
      `}</style>
    </div>
  );
}

// --- MY MEDICINES: list + scan-a-new-medicine conflict check ----------------
function MedsTab({ me, lang, meds, reminders }) {
  return (
    <div className="meds-grid">
      <div className="col" style={{ gap: 14 }}>
        <div>
          <h2 style={{ fontSize: 20 }}>My medicines</h2>
          <p className="muted" style={{ fontSize: 13 }}>What each one is for, and when to take it.</p>
        </div>
        {meds === null && <span className="spinner" />}
        {meds && meds.length === 0 && <div className="card" style={{ padding: 18 }}><div className="muted">No medicines on your record yet.</div></div>}
        {(meds || []).map((m, i) => (
          <div key={i} className="card med-card">
            <div className="row between">
              <b style={{ fontSize: 16 }}>💊 {m.name}</b>
              {m.schedule && <span className="pill" style={{ fontSize: 12 }}>⏰ {m.schedule}</span>}
            </div>
            {m.purpose && <div className="dim" style={{ fontSize: 14, marginTop: 6, lineHeight: 1.5 }}>{m.purpose}</div>}
            {m.detail && <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{m.detail}</div>}
          </div>
        ))}
        {reminders.length > 0 && (
          <div className="card" style={{ padding: 16 }}>
            <b style={{ fontSize: 14 }}>⏰ Reminders that leave with you</b>
            <div className="col" style={{ gap: 6, marginTop: 8 }}>
              {reminders.map((r) => (
                <div key={r.id} className="muted" style={{ fontSize: 13 }}>{r.description}{r.schedule_text ? ` · ${r.schedule_text}` : ""}</div>
              ))}
            </div>
          </div>
        )}
      </div>

      <MedScanner me={me} lang={lang} />

      <style>{`
        .meds-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; align-items:start; }
        .med-card { padding:16px 18px; }
        @media (max-width:900px){ .meds-grid{grid-template-columns:1fr;} }
      `}</style>
    </div>
  );
}

function MedScanner({ me, lang }) {
  const [cameraOn, setCameraOn] = useState(false);
  const [captured, setCaptured] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [typed, setTyped] = useState("");
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const blobRef = useRef(null);

  async function startCam() {
    setResult(null); setCaptured(null); blobRef.current = null;
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } } });
      streamRef.current = s;
      if (videoRef.current) { videoRef.current.srcObject = s; await videoRef.current.play(); }
      setCameraOn(true);
    } catch (e) { alert("Camera not available — type the name instead. (" + e.message + ")"); }
  }
  function stopCam() {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null; setCameraOn(false);
  }
  function capture() {
    const v = videoRef.current, c = canvasRef.current;
    if (!v || !v.videoWidth) return;
    c.width = v.videoWidth; c.height = v.videoHeight;
    c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
    setCaptured(c.toDataURL("image/jpeg", 0.85));
    c.toBlob((b) => (blobRef.current = b), "image/jpeg", 0.85);
  }
  useEffect(() => () => stopCam(), []);

  async function check(useImage) {
    setBusy(true); setResult(null);
    try {
      const payload = useImage ? { file: blobRef.current, language: lang } : { text: typed, language: lang };
      const r = await api.patientMedCheck(me.patient_id, payload);
      setResult(r);
      if (r.found && r.results?.[0]?.message) speak(r.results[0].message, lang);
    } catch (e) { alert(e.message); } finally { setBusy(false); }
  }

  const verdict = result?.found ? (result.safe ? "review" : "conflict") : null;

  return (
    <div className="card" style={{ padding: 18 }}>
      <div className="row" style={{ gap: 8, marginBottom: 4 }}><span style={{ fontSize: 18 }}>📷</span><b>Scan a new medicine</b></div>
      <p className="muted" style={{ fontSize: 13, marginBottom: 12 }}>
        Got a new medicine at home? Show it to me and I'll check it against your allergies and current medicines — on this device.
      </p>

      <div style={{ display: cameraOn ? "block" : "none", marginBottom: 10 }}>
        {captured
          ? <img src={captured} alt="captured" style={{ width: "100%", borderRadius: 10 }} />
          : <video ref={videoRef} playsInline muted style={{ width: "100%", borderRadius: 10 }} />}
        <canvas ref={canvasRef} style={{ display: "none" }} />
      </div>

      <div className="row wrap" style={{ gap: 8 }}>
        {!cameraOn && <button className="btn btn-primary" onClick={startCam}>📷 Open camera</button>}
        {cameraOn && !captured && <><button className="btn btn-primary" onClick={capture}>Capture</button><button className="btn btn-ghost" onClick={stopCam}>Close</button></>}
        {cameraOn && captured && <>
          <button className="btn btn-primary" onClick={() => check(true)} disabled={busy}>{busy ? <span className="spinner" /> : "Check this medicine"}</button>
          <button className="btn btn-ghost" onClick={() => { setCaptured(null); blobRef.current = null; }}>Retake</button>
        </>}
      </div>

      <div className="row" style={{ gap: 8, marginTop: 12 }}>
        <input className="input" placeholder="…or type a medicine name" value={typed}
          onChange={(e) => setTyped(e.target.value)} onKeyDown={(e) => e.key === "Enter" && typed.trim() && check(false)} />
        <button className="btn" onClick={() => check(false)} disabled={busy || !typed.trim()}>Check</button>
      </div>

      {result && (
        <div className={`verdict ${verdict}`}>
          {verdict === "review" && <><div className="v-icon">🔎</div><b>No configured conflict found — confirm before taking</b></>}
          {verdict === "conflict" && <><div className="v-icon">⚠️</div><b>Check with your doctor first</b></>}
          {!result.found && <><div className="v-icon">🤔</div><b>Couldn't read a medicine name</b></>}
          {(result.results || []).map((res, i) => (
            <div key={i} className="v-msg">{res.message}</div>
          ))}
          {!result.found && <div className="v-msg">{result.message}</div>}
          {verdict === "conflict" && (
            <div className="v-conflicts">
              {result.results.flatMap((r) => r.conflicts).map((c, i) => (
                <span key={i} className="tag" style={{ background: "var(--crit-glow)", color: "var(--crit)", fontSize: 11 }}>
                  conflicts with {c.with}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <style>{`
        .verdict { margin-top:14px; padding:16px; border-radius:12px; text-align:center; animation:fadeUp 0.3s ease both; }
        .verdict.review { background:var(--bg-soft); border:1px solid var(--line); }
        .verdict.conflict { background:rgba(255,90,110,0.1); border:1px solid var(--crit);
          animation:fadeUp 0.3s ease both, pulseCrit 1.6s ease 3; }
        .v-icon { font-size:40px; margin-bottom:6px; }
        .v-msg { font-size:15px; line-height:1.55; margin-top:8px; }
        .v-conflicts { display:flex; gap:6px; justify-content:center; flex-wrap:wrap; margin-top:10px; }
      `}</style>
    </div>
  );
}

// --- MY JOURNEY: split by visit, in the patient's language ------------------
function JourneyTab({ me, lang, journey }) {
  const [recaps, setRecaps] = useState({});   // visitId -> recap text
  const [recapBusy, setRecapBusy] = useState(null);
  const data = journey; // prefetched by the parent
  const visits = data?.visits || [];

  async function doRecap(v) {
    setRecapBusy(v.id);
    try {
      const r = await api.patientVisitRecap(me.patient_id, {
        admitted_at: v.admitted_at, discharged_at: v.discharged_at, language: lang,
      });
      setRecaps((m) => ({ ...m, [v.id]: r.recap }));
      speak(r.recap, lang);
    } catch (e) { alert(e.message); } finally { setRecapBusy(null); }
  }

  return (
    <div>
      <div style={{ marginBottom: 14 }}>
        <h2 style={{ fontSize: 20 }}>My journey</h2>
        <p className="muted" style={{ fontSize: 13 }}>Your care, visit by visit. Tap a visit for a plain recap.</p>
      </div>

      {data === null && <span className="spinner" />}
      {data && visits.length === 0 && <div className="card" style={{ padding: 18 }}><div className="muted">Your journey will appear here as your care happens.</div></div>}

      <div className="col" style={{ gap: 16 }}>
        {visits.map((v) => (
          <div key={v.id} className="card visit-card">
            <div className="row between" style={{ marginBottom: 10 }}>
              <b style={{ fontSize: 16 }}>{v.status === "current" ? "This visit" : "Visit"}</b>
              <span className="pill" style={{ fontSize: 11, color: v.status === "current" ? "var(--ok)" : "var(--text-mute)" }}>
                {fmtDay(v.admitted_at)}{v.discharged_at ? ` → ${fmtDay(v.discharged_at)}` : " · ongoing"}
              </span>
            </div>
            <div className="visit-events">
              {v.events.map((e, i) => <span key={i} className="event-chip">{e.icon} {e.label}</span>)}
            </div>

            <button className="btn btn-primary recap-btn" onClick={() => doRecap(v)} disabled={recapBusy === v.id}>
              {recapBusy === v.id ? <span className="spinner" /> : "📖 Recap this visit"}
            </button>
            {recaps[v.id] && (
              <div className="soft-note fade-up">
                {recaps[v.id]}<button className="bubble-speak" onClick={() => speak(recaps[v.id], lang)}>🔊</button>
              </div>
            )}

            {v.red_flags?.length > 0 && (
              <div className="rf-block">
                <div className="rf-head">🚩 When to get help right away</div>
                <div className="rf-grid">
                  {v.red_flags.map((rf, i) => (
                    <div key={i} className="rf-card">
                      <div className="rf-symptom">⚠️ {rf.symptom}</div>
                      {rf.description && <div className="rf-desc">{rf.description}</div>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <style>{`
        .visit-card { padding:18px; }
        .visit-events { display:flex; flex-wrap:wrap; gap:6px; }
        .recap-btn { margin-top:12px; }
        .event-chip { font-size:12px; padding:6px 11px; border-radius:999px; background:var(--panel-2);
          border:1px solid var(--line); color:var(--text-dim); }
        .rf-block { margin-top:14px; padding:14px; border-radius:12px; background:rgba(255,90,110,0.07);
          border:1px solid rgba(255,90,110,0.35); }
        .rf-head { font-weight:700; color:var(--crit); font-size:14px; margin-bottom:10px; }
        .rf-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
        .rf-card { background:var(--bg-soft); border:1px solid rgba(255,90,110,0.25); border-radius:10px; padding:11px 13px; }
        .rf-symptom { font-weight:700; font-size:14px; }
        .rf-desc { font-size:12px; color:var(--text-dim); margin-top:3px; line-height:1.45; }
        @media (max-width:640px){ .rf-grid{grid-template-columns:1fr;} }
      `}</style>
    </div>
  );
}

function fmtDay(iso) {
  try { return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" }); }
  catch { return iso; }
}
