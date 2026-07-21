import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

// The Dashboard — one place to find anything about this patient. At-a-glance vitals,
// the numbers that matter, ask-anything over the whole record, and a single unified
// timeline of every round, document, and Guardian alert this visit.

const TONE_COLORS = {
  anxious: "#ffb84d", distressed: "#ff5a6e", "in pain": "#ff5a6e",
  frustrated: "#ff9db0", calm: "#3ee08a", reassured: "#3ee08a", neutral: "#8a97bd",
};

const SUGGESTED = ["What are her allergies?", "Is she on any blood thinners?", "Why is she here?", "What's still open?"];

export default function VisitsView({ patient, pid, snapshot, setTab }) {
  const [encounters, setEncounters] = useState([]);
  const [docs, setDocs] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [ask, setAsk] = useState("");
  const [answer, setAnswer] = useState(null);
  const [asking, setAsking] = useState(false);
  const [brief, setBrief] = useState(null);
  const [briefing, setBriefing] = useState(false);

  const load = useCallback(async () => {
    const [enc, consent, discharge, rx, rem] = await Promise.all([
      api.scribeEncounters(pid).catch(() => []),
      api.consentList(pid).catch(() => []),
      api.dischargeList(pid).catch(() => []),
      api.prescriptionList(pid).catch(() => []),
      api.reminders(pid).catch(() => []),
    ]);
    setEncounters(enc);
    setDocs([
      ...consent.map((d) => ({ ...d, _kind: "consent" })),
      ...discharge.map((d) => ({ ...d, _kind: "discharge" })),
      ...rx.map((d) => ({ ...d, _kind: "prescription" })),
    ]);
    setReminders(rem);
  }, [pid]);

  useEffect(() => { load(); }, [load]);

  const nodes = snapshot.nodes || [];
  const alerts = snapshot.alerts || [];
  const activeAlerts = alerts.filter((a) => a.status === "active");
  const allergies = nodes.filter((n) => n.ntype === "allergy");
  const meds = nodes.filter((n) => n.ntype === "medication");
  const tones = encounters.map((e) => e.emotional_tone).filter(Boolean).reverse();

  async function doAsk(q) {
    const question = q ?? ask;
    if (!question.trim()) return;
    setAsking(true); setAnswer(null);
    try { setAnswer(await api.askRoom(pid, question, "staff")); }
    catch (e) { setAnswer({ answer: "Could not reach the memory: " + e.message }); }
    finally { setAsking(false); }
  }
  async function catchUp() {
    setBriefing(true);
    try { setBrief(await api.catchMeUp(pid)); }
    catch (e) { setBrief({ briefing: e.message }); }
    finally { setBriefing(false); }
  }

  // Unified activity feed: encounters + documents + alerts, newest first.
  const feed = [
    ...encounters.map((e) => ({ t: e.created_at, type: "encounter", data: e })),
    ...docs.map((d) => ({ t: d.created_at, type: "doc", data: d })),
    ...alerts.map((a) => ({ t: a.created_at, type: "alert", data: a })),
  ].sort((a, b) => new Date(b.t) - new Date(a.t));

  return (
    <div>
      {/* Hero */}
      <div className="dash-hero card">
        <div className="row between" style={{ alignItems: "flex-start" }}>
          <div>
            <div className="muted" style={{ fontSize: 13 }}>Patient dashboard · everything, one place</div>
            <h1 style={{ fontSize: 28, letterSpacing: "-0.02em", marginTop: 2 }}>{patient.name}</h1>
            <div className="muted" style={{ marginTop: 4 }}>
              {patient.age ? `${patient.age} yrs · ` : ""}Room {patient.room || "—"}
              {patient.reason_for_visit ? ` · Here for ${patient.reason_for_visit}` : ""}
            </div>
          </div>
          <span className="tag" style={{
            background: patient.status === "admitted" ? "rgba(62,224,138,0.12)" : "var(--panel-2)",
            color: patient.status === "admitted" ? "var(--ok)" : "var(--text-mute)", fontSize: 12, padding: "5px 10px",
          }}>{patient.status}</span>
        </div>
        {tones.length > 0 && (
          <div className="row" style={{ gap: 8, marginTop: 14 }}>
            <span className="muted" style={{ fontSize: 12 }}>Mood over the visit</span>
            <div className="row" style={{ gap: 5 }}>
              {tones.map((t, i) => (
                <span key={i} title={t} className="mood-dot" style={{ background: TONE_COLORS[String(t).toLowerCase()] || "#8a97bd" }} />
              ))}
            </div>
            <span className="muted" style={{ fontSize: 12 }}>→ {tones[tones.length - 1]}</span>
          </div>
        )}
      </div>

      {/* Stat tiles */}
      <div className="stat-row">
        <Stat n={nodes.length} label="facts remembered" onClick={() => setTab("overview")} />
        <Stat n={activeAlerts.length} label="open concerns" tone={activeAlerts.length ? "crit" : "ok"} onClick={() => setTab("overview")} />
        <Stat n={meds.length} label="medications" />
        <Stat n={allergies.length} label="allergies" tone={allergies.length ? "warn" : undefined} />
        <Stat n={encounters.length} label="rounds captured" onClick={() => setTab("scribe")} />
      </div>

      <div className="dash-grid">
        <div className="col" style={{ gap: 16 }}>
          {/* Ask anything */}
          <div className="card" style={{ padding: 18 }}>
            <div className="row between" style={{ marginBottom: 10 }}>
              <div className="row" style={{ gap: 8 }}><span style={{ fontSize: 16 }}>💬</span><b>Ask anything</b></div>
              <button className="btn btn-ghost" style={{ padding: "6px 10px", fontSize: 12 }} onClick={catchUp} disabled={briefing}>
                {briefing ? <span className="spinner" /> : "⏱ Catch me up"}
              </button>
            </div>
            <div className="row" style={{ gap: 8 }}>
              <input className="input" placeholder="Ask about anything on the record…" value={ask}
                onChange={(e) => setAsk(e.target.value)} onKeyDown={(e) => e.key === "Enter" && doAsk()} />
              <button className="btn btn-primary" onClick={() => doAsk()} disabled={asking}>
                {asking ? <span className="spinner" /> : "Ask"}
              </button>
            </div>
            <div className="row wrap" style={{ gap: 6, marginTop: 10 }}>
              {SUGGESTED.map((q) => <button key={q} className="chip" onClick={() => { setAsk(q); doAsk(q); }}>{q}</button>)}
            </div>
            {answer && (
              <div className="answer fade-up">
                <span style={{ color: "var(--teal)", fontSize: 12, fontWeight: 700 }}>◈ CONFIDE</span>
                <div style={{ marginTop: 4 }}>{answer.answer}</div>
              </div>
            )}
            {brief && (
              <div className="answer fade-up" style={{ marginTop: 10 }}>
                <span style={{ color: "var(--teal)", fontSize: 12, fontWeight: 700 }}>◈ 15-SECOND BRIEFING</span>
                <div style={{ marginTop: 4 }}>{brief.briefing}</div>
              </div>
            )}
          </div>

          {/* At a glance */}
          <div className="card" style={{ padding: 18 }}>
            <b style={{ fontSize: 14 }}>At a glance</b>
            <Glance label="Allergies" empty="None on file" items={allergies.map((a) => a.label)} tone="crit" />
            <Glance label="Current medications" empty="None recorded" items={meds.map((m) => m.label)} tone="blue" />
            {reminders.length > 0 && (
              <Glance label="Take-home reminders" empty="" items={reminders.map((r) => r.description + (r.schedule_text ? ` · ${r.schedule_text}` : ""))} />
            )}
          </div>
        </div>

        {/* Unified timeline */}
        <div className="card" style={{ padding: 18 }}>
          <div className="row between" style={{ marginBottom: 12 }}>
            <b style={{ fontSize: 14 }}>Everything that happened</b>
            <span className="muted" style={{ fontSize: 12 }}>{feed.length} events</span>
          </div>
          {feed.length === 0 && <div className="muted" style={{ fontSize: 13 }}>Nothing captured yet.</div>}
          <div className="timeline">
            {feed.map((item, i) => <FeedItem key={i} item={item} />)}
          </div>
        </div>
      </div>

      <style>{`
        .dash-hero { padding:22px 24px; margin-bottom:16px; }
        .mood-dot { width:10px; height:10px; border-radius:50%; display:inline-block; }
        .stat-row { display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-bottom:16px; }
        .stat { padding:16px 18px; text-align:left; transition:all .15s; }
        .stat:hover { border-color:var(--teal-dim); }
        .dash-grid { display:grid; grid-template-columns:1fr 1.05fr; gap:16px; align-items:start; }
        .answer { margin-top:12px; background:rgba(47,230,200,0.06); border:1px solid var(--teal-dim);
          border-radius:10px; padding:12px 14px; font-size:14px; line-height:1.55; }
        .chip { font-size:12px; padding:6px 11px; border-radius:999px; background:var(--panel-2);
          border:1px solid var(--line); color:var(--text-dim); }
        .chip:hover { border-color:var(--teal-dim); color:var(--text); }
        .timeline { display:flex; flex-direction:column; }
        @media(max-width:1000px){ .stat-row{grid-template-columns:repeat(2,1fr);} .dash-grid{grid-template-columns:1fr;} }
      `}</style>
    </div>
  );
}

function Stat({ n, label, tone, onClick }) {
  const color = tone === "crit" ? "var(--crit)" : tone === "warn" ? "var(--warn)" : tone === "ok" ? "var(--ok)" : "var(--text)";
  return (
    <button className="card stat" onClick={onClick} style={{ cursor: onClick ? "pointer" : "default" }}>
      <div style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-0.03em", color }}>{n}</div>
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
    </button>
  );
}

function Glance({ label, items, empty, tone }) {
  const color = tone === "crit" ? "var(--crit)" : tone === "blue" ? "var(--blue)" : "var(--text-dim)";
  return (
    <div style={{ marginTop: 12 }}>
      <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>{label}</div>
      {items.length ? (
        <div className="row wrap" style={{ gap: 6 }}>
          {items.map((it, i) => (
            <span key={i} className="tag" style={{ background: "var(--panel-2)", color, fontSize: 12, padding: "4px 9px", textTransform: "none", letterSpacing: 0 }}>{it}</span>
          ))}
        </div>
      ) : empty ? <div className="muted" style={{ fontSize: 13 }}>{empty}</div> : null}
    </div>
  );
}

const DOC_META = {
  consent: { icon: "📋", label: "Consent explained", color: "var(--violet)" },
  discharge: { icon: "🏠", label: "Discharge plan", color: "var(--teal)" },
  prescription: { icon: "℞", label: "Prescription added", color: "var(--blue)" },
};
const SEV_COLOR = { critical: "var(--crit)", warning: "var(--warn)", info: "var(--teal)" };

function FeedItem({ item }) {
  const [open, setOpen] = useState(false);
  let icon, color, title, sub, body;
  if (item.type === "encounter") {
    const e = item.data;
    icon = e.kind === "admission" ? "➕" : "🎧"; color = "var(--teal)";
    title = e.chief_complaint || (e.kind === "admission" ? "Admission" : "Round note");
    sub = e.kind; body = e.summary;
  } else if (item.type === "doc") {
    const m = DOC_META[item.data._kind] || { icon: "📄", label: "Document", color: "var(--text-dim)" };
    icon = m.icon; color = m.color; title = m.label; body = item.data.explanation;
  } else {
    const a = item.data;
    icon = "🛡"; color = SEV_COLOR[a.severity] || "var(--teal)";
    title = a.title; sub = a.status !== "active" ? a.status : "Guardian"; body = a.message;
  }
  return (
    <div className="tl-item">
      <span className="tl-dot" style={{ background: color }}>{icon}</span>
      <div className="tl-body">
        <div className="row between">
          <b style={{ fontSize: 14 }}>{title}</b>
          <span className="muted" style={{ fontSize: 11 }}>{fmt(item.t)}</span>
        </div>
        {sub && <div className="muted" style={{ fontSize: 11, textTransform: "capitalize" }}>{sub}</div>}
        {body && <div className="dim" style={{ fontSize: 13, marginTop: 4, lineHeight: 1.5 }}>{body}</div>}
        {item.type === "encounter" && item.data.raw_transcript && (
          <>
            <button className="tl-more" onClick={() => setOpen((v) => !v)}>{open ? "Hide" : "Transcript"}</button>
            {open && <div className="muted" style={{ fontSize: 12, marginTop: 6, lineHeight: 1.5 }}>{item.data.raw_transcript}</div>}
          </>
        )}
      </div>
      <style>{`
        .tl-item { display:flex; gap:14px; padding:0 0 18px; position:relative; }
        .tl-item:last-child { padding-bottom:0; }
        /* Spine connecting the dots into one continuous timeline. */
        .tl-item:not(:last-child)::before { content:""; position:absolute; left:15px; top:34px; bottom:0;
          width:2px; background:linear-gradient(var(--line), var(--line-soft)); }
        .tl-dot { width:32px; height:32px; border-radius:10px; display:grid; place-items:center; font-size:15px;
          flex-shrink:0; background:var(--panel-hi); border:1px solid var(--line); position:relative; z-index:1; }
        .tl-body { flex:1; min-width:0; background:var(--panel-2); border:1px solid var(--line-soft);
          border-radius:10px; padding:11px 13px; transition:border-color .15s; }
        .tl-body:hover { border-color:var(--teal-dim); }
        .tl-more { font-size:11px; color:var(--text-mute); margin-top:6px; }
        .tl-more:hover { color:var(--teal); }
      `}</style>
    </div>
  );
}

function fmt(iso) {
  try { return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); }
  catch { return iso; }
}
