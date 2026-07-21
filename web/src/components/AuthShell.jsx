import { Link } from "react-router-dom";
import NetworkPill from "./NetworkPill.jsx";

export default function AuthShell({ icon, title, subtitle, audience = "CareTrace workspace", children }) {
  return (
    <div className="auth-page">
      <header className="auth-nav"><Link to="/" className="auth-brand"><span>✦</span><b>CareTrace</b></Link><NetworkPill /></header>
      <main className="auth-main">
        <section className="auth-story fade-up">
          <div className="auth-kicker"><i />{audience.toUpperCase()}</div>
          <h1>Care context,<br /><em>kept close.</em></h1>
          <p>One local workspace for the patient story, safety signals, and the next conversation.</p>
          <div className="auth-proof"><span>🔒</span><div><b>Data stays in this workspace</b><small>Local storage and on-device GPT-OSS inference.</small></div></div>
          <div className="auth-steps"><span>01 · Capture facts</span><span>02 · Review evidence</span><span>03 · Hand off clearly</span></div>
        </section>
        <section className="auth-card card fade-up" style={{ animationDelay: "0.08s" }}>
          <div className="auth-icon">{icon}</div>
          <div className="auth-card-kicker">SECURE LOCAL ACCESS</div>
          <h2>{title}</h2>
          <p className="muted">{subtitle}</p>
          <div className="auth-rule" />
          {children}
        </section>
      </main>
      <footer className="auth-foot">Clinical decision support only <span>•</span> Synthetic demo data only</footer>
      <style>{`
        .auth-page{min-height:100%;position:relative;overflow:hidden;display:flex;flex-direction:column}.auth-page::before{content:"";position:absolute;width:680px;height:680px;border-radius:50%;right:-220px;top:-310px;border:1px solid rgba(100,232,210,.18);box-shadow:0 0 0 70px rgba(100,232,210,.03),0 0 0 145px rgba(100,232,210,.018);pointer-events:none}.auth-nav{width:min(1180px,100%);margin:auto;padding:24px 32px;display:flex;align-items:center;justify-content:space-between;position:relative;z-index:1}.auth-brand{color:var(--text);display:inline-flex;align-items:center;gap:9px;font-size:19px;letter-spacing:-.03em}.auth-brand span{color:var(--teal);font-size:23px}.auth-main{width:min(1040px,100%);margin:auto;flex:1;display:grid;grid-template-columns:1fr 420px;align-items:center;gap:88px;padding:54px 32px}.auth-kicker,.auth-card-kicker{font-size:10px;font-weight:800;letter-spacing:.13em;color:var(--teal)}.auth-kicker{display:flex;align-items:center;gap:8px}.auth-kicker i{width:7px;height:7px;border-radius:50%;background:var(--teal);box-shadow:0 0 0 5px rgba(100,232,210,.12)}.auth-story h1{margin:18px 0;font-size:clamp(44px,5vw,64px);line-height:.98;letter-spacing:-.065em}.auth-story h1 em{font-style:normal;color:var(--teal)}.auth-story>p{font-size:17px;line-height:1.65;color:var(--text-dim);max-width:480px}.auth-proof{display:flex;gap:11px;align-items:flex-start;margin-top:28px;padding:13px 14px;max-width:430px;border:1px solid rgba(100,232,210,.25);border-radius:12px;background:rgba(100,232,210,.07)}.auth-proof>span{font-size:16px}.auth-proof b,.auth-proof small{display:block}.auth-proof b{font-size:13px;color:var(--teal)}.auth-proof small{margin-top:2px;font-size:11px;color:var(--text-mute)}.auth-steps{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px;color:var(--text-mute);font-size:10px;font-weight:700;letter-spacing:.06em}.auth-steps span{padding-right:10px;border-right:1px solid var(--line)}.auth-steps span:last-child{border:none}.auth-card{padding:34px;position:relative;overflow:hidden}.auth-card::after{content:"";position:absolute;width:170px;height:170px;right:-90px;top:-90px;border-radius:50%;background:radial-gradient(circle,rgba(100,232,210,.17),transparent 68%);pointer-events:none}.auth-icon{width:48px;height:48px;display:grid;place-items:center;border-radius:14px;background:linear-gradient(145deg,rgba(100,232,210,.2),rgba(100,232,210,.06));border:1px solid rgba(100,232,210,.27);font-size:23px;margin-bottom:18px}.auth-card h2{font-size:27px;letter-spacing:-.04em;margin:5px 0 6px}.auth-card>p{font-size:14px;line-height:1.55}.auth-rule{height:1px;background:var(--line-soft);margin:22px 0}.auth-foot{width:min(1180px,100%);margin:auto;padding:22px 32px 30px;color:var(--text-mute);font-size:11px;display:flex;gap:9px}.auth-foot span{color:var(--line)}@media(max-width:820px){.auth-main{grid-template-columns:1fr;gap:34px;padding:30px 22px}.auth-story{max-width:520px}.auth-card{width:min(100%,460px)}.auth-nav,.auth-foot{padding-left:22px;padding-right:22px}}@media(max-width:480px){.auth-card{padding:26px 22px}.auth-story h1{font-size:46px}.auth-steps span{border:none}}
      `}</style>
    </div>
  );
}
