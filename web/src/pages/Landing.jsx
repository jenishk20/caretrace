import { Link } from "react-router-dom";
import NetworkPill from "../components/NetworkPill.jsx";

export default function Landing() {
  return (
    <div className="landing">
      <div className="row between" style={{ padding: "22px 32px" }}>
        <div className="row" style={{ gap: 10 }}>
          <span className="logo-mark">◈</span>
          <b style={{ fontSize: 18, letterSpacing: "-0.01em" }}>Confide</b>
        </div>
        <NetworkPill />
      </div>

      <div className="hero">
        <div className="hero-eyebrow fade-up">On-device · powered by gpt-oss · works with the network off</div>
        <h1 className="fade-up" style={{ animationDelay: "0.05s" }}>
          A second clinician in the room<br />that never forgets.
        </h1>
        <p className="hero-sub fade-up" style={{ animationDelay: "0.1s" }}>
          Confide hears every conversation, remembers everything in one living patient model, and
          watches over the care — catching the mistakes people make when they're tired and busy.
        </p>

        <div className="cap-row fade-up" style={{ animationDelay: "0.15s" }}>
          <Cap icon="🎧" title="Hear" text="Live understanding of conversation and plain-language explanation." />
          <Cap icon="🧠" title="Remember" text="One living knowledge graph, built from every interaction." />
          <Cap icon="🛡" title="Watch over" text="The Guardian checks what's said against the record — and speaks up on its own." />
        </div>

        <div className="tabs fade-up" style={{ animationDelay: "0.2s" }}>
          <Link to="/doctor/login" className="tab-card">
            <div className="tab-icon">🩺</div>
            <div>
              <div className="tab-title">I'm a clinician</div>
              <div className="tab-sub">Round, capture, and watch the Guardian work</div>
            </div>
            <span className="tab-go">→</span>
          </Link>
          <Link to="/patient/login" className="tab-card">
            <div className="tab-icon">💙</div>
            <div>
              <div className="tab-title">I'm a patient</div>
              <div className="tab-sub">Ask what's happening to you, in plain language</div>
            </div>
            <span className="tab-go">→</span>
          </Link>
        </div>

        <div className="demo-hint muted fade-up" style={{ animationDelay: "0.25s" }}>
          Demo logins — clinician <code>doctor / confide</code> · patient <code>maria / confide</code>
        </div>
      </div>

      <style>{`
        .landing { min-height:100%; display:flex; flex-direction:column; }
        .logo-mark { color:var(--teal); font-size:22px; filter:drop-shadow(0 0 12px var(--teal-glow)); }
        .hero { max-width:920px; margin:0 auto; padding:40px 32px 60px; text-align:center; }
        .hero-eyebrow { display:inline-block; font-size:13px; font-weight:600; color:var(--teal);
          background:rgba(47,230,200,0.08); border:1px solid var(--teal-dim); padding:6px 14px;
          border-radius:999px; margin-bottom:28px; }
        .hero h1 { font-size:clamp(34px,5vw,54px); line-height:1.08; letter-spacing:-0.03em; margin-bottom:20px; }
        .hero-sub { font-size:18px; color:var(--text-dim); max-width:640px; margin:0 auto 40px; line-height:1.6; }
        .cap-row { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-bottom:44px; text-align:left; }
        .cap { background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); padding:20px; }
        .cap-icon { font-size:22px; margin-bottom:10px; }
        .cap-title { font-weight:700; margin-bottom:6px; }
        .cap-text { font-size:13px; color:var(--text-mute); line-height:1.5; }
        .tabs { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:22px; }
        .tab-card { display:flex; align-items:center; gap:16px; text-align:left; padding:22px 24px;
          background:linear-gradient(180deg,var(--panel-2),var(--panel)); border:1px solid var(--line);
          border-radius:var(--radius); color:var(--text); transition:all 0.18s; }
        .tab-card:hover { border-color:var(--teal-dim); transform:translateY(-2px); box-shadow:var(--shadow-lg); }
        .tab-icon { font-size:30px; }
        .tab-title { font-weight:700; font-size:17px; }
        .tab-sub { font-size:13px; color:var(--text-mute); }
        .tab-go { margin-left:auto; font-size:22px; color:var(--teal); }
        .demo-hint code { background:var(--panel-2); padding:2px 7px; border-radius:6px; color:var(--text-dim);
          font-family:var(--mono); font-size:12px; }
        @media (max-width:760px){ .cap-row,.tabs{grid-template-columns:1fr;} }
      `}</style>
    </div>
  );
}

function Cap({ icon, title, text }) {
  return (
    <div className="cap">
      <div className="cap-icon">{icon}</div>
      <div className="cap-title">{title}</div>
      <div className="cap-text">{text}</div>
    </div>
  );
}
