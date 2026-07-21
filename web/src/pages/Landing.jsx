import { Link } from "react-router-dom";
import NetworkPill from "../components/NetworkPill.jsx";

const proofPoints = [
  ["01", "Capture", "Turn a conversation into reviewable, source-linked facts."],
  ["02", "Connect", "Keep every visit in one living patient record."],
  ["03", "Guard", "Surface deterministic concerns before a handoff is missed."],
];

export default function Landing() {
  return (
    <div className="landing">
      <header className="landing-nav">
        <Link to="/" className="brand" aria-label="MedSignal home"><span>✦</span><b>MedSignal</b></Link>
        <div className="row" style={{ gap: 14 }}><span className="nav-note">LOCAL CLINICAL INTELLIGENCE</span><NetworkPill /></div>
      </header>

      <main className="landing-main">
        <section className="landing-hero">
          <div className="hero-copy fade-up">
            <div className="eyebrow"><i />EVIDENCE-LINKED · CLINICIAN-REVIEWED</div>
            <h1>Bring the whole<br /><em>patient story</em> into view.</h1>
            <p>MedSignal gives care teams a calm, local workspace for encounters, safety checks, and handoffs—without sending patient context to the cloud.</p>
            <div className="privacy-note"><span>🔒</span><p><b>Data never leaves this workspace.</b> MedSignal stores records locally and uses the on-device GPT-OSS model only.</p></div>
            <div className="hero-actions">
              <Link to="/doctor/login" className="hero-cta primary"><span>🩺</span><div><b>Open clinical workspace</b><small>Capture, review, and hand off</small></div><strong>→</strong></Link>
              <Link to="/patient/login" className="hero-cta"><span>💙</span><div><b>Open patient space</b><small>Understand care in plain language</small></div><strong>→</strong></Link>
            </div>
            <div className="hero-trust"><span>◈ GPT-OSS 20B via Ollama</span><span>▣ SQLite evidence store</span><span>◌ Network optional</span></div>
          </div>

          <aside className="signal-card fade-up" style={{ animationDelay: "0.08s" }}>
            <div className="signal-top"><div><span className="signal-label">LIVE MEDSIGNAL SIGNAL</span><h2>One record. One next step.</h2></div><span className="signal-dot" /></div>
            <div className="signal-patient"><div className="signal-avatar">MG</div><div><b>María González</b><small>68 · Room 4B · Chest pain</small></div><span className="safe-pill">LOCAL</span></div>
            <div className="signal-line"><span className="line-node teal" /><div><b>New encounter captured</b><small>Source-linked fact set ready for review</small></div></div>
            <div className="signal-line"><span className="line-node blue" /><div><b>Patient graph updated</b><small>Medication, observation, and follow-up connected</small></div></div>
            <div className="signal-alert"><span>🛡</span><div><b>Guardian is watching</b><small>Deterministic checks run only on confirmed facts.</small></div></div>
            <div className="signal-foot"><span>MODEL RESIDENT</span><b>gpt-oss:20b</b><span>•</span><b>ON DEVICE</b></div>
          </aside>
        </section>

        <section className="proof-grid">
          {proofPoints.map(([number, title, text]) => <article key={number} className="proof-card"><span>{number}</span><h3>{title}</h3><p>{text}</p></article>)}
        </section>
      </main>

      <footer className="landing-foot"><span>Clinical decision support only</span><span>•</span><span>Synthetic demo data only</span><span>•</span><span>Every Guardian item requires clinician review</span></footer>

      <style>{`
        .landing { min-height:100%; position:relative; overflow:hidden; }
        .landing::before { content:""; position:absolute; width:720px; height:720px; right:-310px; top:-320px; border:1px solid rgba(100,232,210,.14); border-radius:50%; box-shadow:0 0 0 70px rgba(100,232,210,.025),0 0 0 150px rgba(100,232,210,.018); pointer-events:none; }
        .landing-nav { width:min(1220px,100%); margin:auto; padding:24px 34px; display:flex; justify-content:space-between; align-items:center; position:relative; z-index:1; }
        .brand { display:inline-flex; align-items:center; gap:9px; color:var(--text); font-size:19px; letter-spacing:-.03em; }.brand span{color:var(--teal);font-size:23px}.nav-note{font-size:10px;font-weight:800;letter-spacing:.13em;color:var(--text-mute)}
        .landing-main { width:min(1220px,100%); margin:auto; padding:48px 34px 56px; position:relative; z-index:1; }
        .landing-hero { display:grid; grid-template-columns:1.08fr .92fr; gap:62px; align-items:center; min-height:530px; }
        .eyebrow { display:inline-flex; align-items:center; gap:8px; color:var(--teal); font-size:11px; font-weight:800; letter-spacing:.13em; }.eyebrow i{width:7px;height:7px;border-radius:50%;background:var(--teal);box-shadow:0 0 0 5px rgba(100,232,210,.13)}
        .hero-copy h1 { margin:20px 0 18px; max-width:650px; font-size:clamp(48px,6.3vw,76px); line-height:.99; letter-spacing:-.065em; }.hero-copy h1 em { color:var(--teal); font-style:normal; }.hero-copy>p { max-width:610px; font-size:18px; line-height:1.65; color:var(--text-dim); }
        .privacy-note { display:flex; align-items:flex-start; gap:10px; max-width:610px; margin-top:18px; padding:11px 13px; border:1px solid rgba(100,232,210,.25); border-radius:11px; background:rgba(100,232,210,.07); }.privacy-note span{font-size:15px}.privacy-note p{color:var(--text-dim);font-size:12px;line-height:1.55}.privacy-note b{color:var(--teal); }
        .hero-actions { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:34px; }.hero-cta { min-height:88px; display:flex; align-items:center; gap:11px; padding:16px; border-radius:14px; border:1px solid var(--line); background:rgba(13,38,49,.78); color:var(--text); transition:transform .16s, border-color .16s, background .16s; }.hero-cta:hover{transform:translateY(-3px);border-color:var(--teal-dim);background:rgba(22,60,71,.9)}.hero-cta.primary{background:linear-gradient(130deg,rgba(100,232,210,.2),rgba(27,83,96,.8));border-color:rgba(100,232,210,.42)}.hero-cta>span{font-size:24px}.hero-cta div{min-width:0}.hero-cta b{display:block;font-size:14px}.hero-cta small{display:block;color:var(--text-mute);font-size:11px;margin-top:3px}.hero-cta strong{margin-left:auto;color:var(--teal);font-size:21px}
        .hero-trust { display:flex; flex-wrap:wrap; gap:12px; margin-top:20px; color:var(--text-mute); font-size:11px; }.hero-trust span{padding-right:12px;border-right:1px solid var(--line)}.hero-trust span:last-child{border:none}
        .signal-card { padding:22px; border:1px solid rgba(100,232,210,.26); border-radius:22px; background:linear-gradient(145deg,rgba(29,75,85,.7),rgba(8,27,37,.94) 58%); box-shadow:var(--shadow-lg); }.signal-top{display:flex;justify-content:space-between;gap:14px;padding-bottom:18px;border-bottom:1px solid var(--line-soft)}.signal-label{font-size:10px;color:var(--teal);font-weight:800;letter-spacing:.12em}.signal-top h2{font-size:22px;letter-spacing:-.035em;margin-top:4px}.signal-dot{width:10px;height:10px;border-radius:50%;background:var(--ok);box-shadow:0 0 0 6px rgba(62,224,138,.1);margin-top:7px}.signal-patient{display:flex;align-items:center;gap:10px;padding:18px 0}.signal-avatar{width:40px;height:40px;display:grid;place-items:center;border-radius:12px;background:linear-gradient(145deg,var(--panel-hi),var(--bg-soft));border:1px solid var(--line);color:var(--teal);font-weight:800;font-size:13px}.signal-patient b{display:block;font-size:14px}.signal-patient small,.signal-line small,.signal-alert small{display:block;color:var(--text-mute);font-size:11px;margin-top:2px}.safe-pill{margin-left:auto;border:1px solid rgba(100,232,210,.32);color:var(--teal);font-size:9px;font-weight:800;letter-spacing:.1em;padding:4px 6px;border-radius:999px}.signal-line{display:flex;gap:12px;padding:10px 0 10px 6px;position:relative}.signal-line::before{content:"";position:absolute;left:10px;top:29px;width:1px;height:26px;background:var(--line)}.signal-line:last-of-type::before{display:none}.line-node{width:9px;height:9px;border-radius:50%;margin-top:5px;flex:none}.line-node.teal{background:var(--teal);box-shadow:0 0 0 5px rgba(100,232,210,.1)}.line-node.blue{background:var(--blue);box-shadow:0 0 0 5px rgba(118,169,255,.1)}.signal-line b,.signal-alert b{font-size:13px}.signal-alert{display:flex;gap:11px;padding:13px;margin-top:9px;border:1px solid rgba(247,200,111,.28);border-radius:11px;background:rgba(247,200,111,.07)}.signal-alert>span{font-size:17px}.signal-foot{display:flex;gap:7px;align-items:center;margin-top:18px;padding-top:13px;border-top:1px solid var(--line-soft);font-size:9px;letter-spacing:.08em;color:var(--text-mute)}.signal-foot b{font-size:10px;color:var(--text-dim)}
        .proof-grid { display:grid;grid-template-columns:repeat(3,1fr);gap:14px;border-top:1px solid var(--line-soft);padding-top:28px; }.proof-card{padding:4px 16px 4px 0;border-right:1px solid var(--line-soft)}.proof-card:last-child{border:none}.proof-card span{color:var(--teal);font-size:11px;font-weight:800;letter-spacing:.1em}.proof-card h3{font-size:18px;margin:5px 0}.proof-card p{max-width:270px;color:var(--text-mute);font-size:13px;line-height:1.55}.landing-foot{width:min(1220px,100%);margin:auto;padding:20px 34px 30px;color:var(--text-mute);font-size:11px;display:flex;justify-content:center;gap:10px;border-top:1px solid var(--line-soft)}
        @media(max-width:900px){.landing-hero{grid-template-columns:1fr;gap:42px}.signal-card{max-width:640px}.hero-copy h1{font-size:clamp(46px,10vw,68px)}}@media(max-width:640px){.landing-nav,.landing-main{padding-left:20px;padding-right:20px}.nav-note{display:none}.landing-main{padding-top:28px}.hero-actions,.proof-grid{grid-template-columns:1fr}.proof-card{padding:12px 0;border-right:none;border-bottom:1px solid var(--line-soft)}.hero-trust span{border:none}.landing-foot{padding:18px 20px 26px;flex-wrap:wrap}.landing-foot span:nth-child(even){display:none}}
      `}</style>
    </div>
  );
}
