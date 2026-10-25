import { useNavigate } from 'react-router-dom'
import './Landing.css'
import aicraftLogo from '../assets/aicraft-logo-dark.png'

// The explanation file. Everything on this page is written from the proxy
// source (backend/app/routers/proxy.py) — if the code changes, change this page.

const STORED = [
  ['Process label', 'the name you gave it, e.g. "gpt-4o-agent"'],
  ['Provider & model', 'e.g. anthropic / claude-sonnet-4-6'],
  ['Token counts', 'input, output, cached, cache-write'],
  ['Computed cost', 'priced from the public rate card'],
  ['Timestamp', 'when the call happened'],
]

const NEVER_STORED = [
  ['Your prompts', 'request bodies are forwarded, parsed for nothing'],
  ['Your responses', 'read in transit for the usage block only, then discarded'],
  ['Your provider API key', 'passes through in the header, never written anywhere'],
  ['Your other headers', 'forwarded to the provider, not logged'],
]

const PROVIDERS: Array<[string, string]> = [
  ['Anthropic', 'JSON + SSE streaming'],
  ['OpenAI', 'JSON + SSE streaming'],
  ['Google Gemini', 'JSON + SSE streaming'],
  ['Azure OpenAI', 'your resource name in the URL'],
  ['AWS Bedrock', 'your region in the URL'],
  ['Groq', 'OpenAI-compatible'],
  ['Mistral', 'OpenAI-compatible'],
  ['xAI', 'OpenAI-compatible'],
  ['Together', 'OpenAI-compatible'],
  ['OpenRouter', 'OpenAI-compatible'],
  ['Fireworks', 'OpenAI-compatible'],
  ['DeepInfra', 'OpenAI-compatible'],
  ['Perplexity', 'OpenAI-compatible'],
  ['Replicate', 'kill switch + pass-through*'],
]

const FAQ = [
  {
    q: 'What does the proxy add to my latency?',
    a: 'One HTTP hop. The proxy streams the provider’s response back to you as it arrives — it never buffers a streamed response to inspect it. The kill-switch check is a single indexed database lookup before the forward.',
  },
  {
    q: 'What happens if CostWindow goes down?',
    a: 'You point your base URL back at the provider and carry on — your key never depended on us. That’s deliberate: the proxy is a pass-through, not a dependency. No lock-in is a feature.',
  },
  {
    q: 'How does the hard stop actually refuse a call?',
    a: 'When a process is killed or its budget hits 100%, the proxy returns a provider-shaped 403 error before anything is sent upstream. Your SDK sees a normal API error and stops. The provider never receives the request, so it can’t bill you for it.',
  },
  {
    q: 'How do you know my real balance if providers have no balance API?',
    a: 'They don’t — no public balance API exists for Anthropic or OpenAI, so any tool claiming to read your balance automatically isn’t. You enter your console balance when you check or top up; CostWindow counts tracked spend down from that entry, shows runway in days, and flags any gap between what left your account and what tracking explains.',
  },
  {
    q: 'And subscriptions — Claude Pro, ChatGPT Plus?',
    a: 'Entered once, by you — cost and renewal day. There’s no API for someone else’s Stripe receipts, so we don’t pretend to automate it. They sit in the same dashboard so the total you see is your actual total.',
  },
  {
    q: 'Is there an SDK if I want more than the proxy?',
    a: 'Yes — pip install costwindow. The Python SDK wraps Anthropic, OpenAI, and Gemini clients, and a one-command hook tracks Claude Code sessions. The proxy is the zero-code path; the SDK is the in-code path. Both feed the same dashboard and obey the same kill switches.',
  },
]

export default function HowItWorks() {
  const navigate = useNavigate()

  return (
    <div className="lp">
      {/* ── Nav ────────────────────────────────────────── */}
      <nav className="lp-nav">
        <div className="lp-nav-brand">
          <span className="lp-nav-logo" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>CostWindow</span>
          <div className="lp-nav-sep" />
          <a className="lp-nav-partner" href="https://myaicraft.uk" target="_blank" rel="noopener noreferrer">
            <img src={aicraftLogo} alt="AiCraft Holdings" style={{ height: 22, width: 'auto', mixBlendMode: 'screen', opacity: 0.85 }} />
          </a>
        </div>
        <div className="lp-nav-actions">
          <button className="lp-btn-ghost" onClick={() => navigate('/login')}>Sign in</button>
          <button className="lp-btn-primary" onClick={() => navigate('/register')} style={{ cursor: 'pointer', border: 'none' }}>Start free</button>
        </div>
      </nav>

      {/* ── Header ─────────────────────────────────────── */}
      <section className="lp-section" style={{ paddingBottom: 24 }}>
        <div className="lp-section-inner lp-section-center">
          <div className="lp-eyebrow">The explanation file</div>
          <h1 className="lp-section-h2" style={{ marginBottom: 20 }}>
            How CostWindow works<span className="lp-h-dash"> —</span><br />and exactly <em>what it sees.</em>
          </h1>
          <p className="lp-section-lead" style={{ maxWidth: 560, margin: '0 auto' }}>
            You&rsquo;re routing production AI traffic through us. You should know precisely
            what happens to every byte. This page is written from the proxy source code,
            not the marketing copy — when the code changes, this page changes.
          </p>
        </div>
      </section>

      {/* ── The request path ───────────────────────────── */}
      <section className="lp-section" style={{ paddingTop: 24 }}>
        <div className="lp-section-inner">
          <div className="lp-eyebrow">01 · The request path</div>
          <h2 className="lp-section-h2" style={{ fontSize: 28, marginBottom: 24 }}>One hop. Two outcomes.</h2>
          <div className="lp-code" style={{ maxWidth: 720 }}>
            <span className="c">┌ your app / agent / cron job{'\n'}</span>
            <span className="c">│    base_url = api.costwindow.com/proxy/anthropic/&lt;cw_key&gt;{'\n'}</span>
            <span className="c">▼{'\n'}</span>
            <span className="kw">CostWindow proxy</span><span className="c">  — one check: is this process allowed to spend?{'\n'}</span>
            <span className="c">│{'\n'}</span>
            <span className="c">├─ allowed ──▶ forwarded to the provider, byte-for-byte, key untouched{'\n'}</span>
            <span className="c">│              response streams straight back to you{'\n'}</span>
            <span className="c">│              usage block read in transit → tokens, model, cost recorded{'\n'}</span>
            <span className="c">│{'\n'}</span>
            <span className="c">└─ killed or over budget ──▶ </span><span className="s">403, provider-shaped, refused here</span><span className="c">{'\n'}</span>
            <span className="c">               the provider is never called. Nothing is billed.{'\n'}</span>
          </div>
          <p className="lp-feat-body" style={{ maxWidth: 640, marginTop: 20 }}>
            That&rsquo;s the whole product mechanic. The proxy exists so the kill switch can
            be a <strong>hard stop</strong> — a refusal before the money moves — rather than
            an alert you read the morning after.
          </p>
        </div>
      </section>

      {/* ── What is stored ─────────────────────────────── */}
      <section className="lp-section lp-section-alt">
        <div className="lp-section-inner">
          <div className="lp-eyebrow">02 · The data</div>
          <h2 className="lp-section-h2" style={{ fontSize: 28, marginBottom: 8 }}>
            Stored per call. <em>Never stored, full stop.</em>
          </h2>
          <p className="lp-feat-body" style={{ maxWidth: 640, marginBottom: 32 }}>
            A tracked call writes one row: the accounting, nothing else. Streamed responses
            are parsed in transit for the usage frames the provider already includes, and
            the content is discarded as it passes through.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20, maxWidth: 760 }}>
            <div className="lp-problem-card" style={{ textAlign: 'left' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.12em', color: '#1DC85E', marginBottom: 14 }}>RECORDED</div>
              {STORED.map(([k, v]) => (
                <div key={k} style={{ padding: '7px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ fontSize: 13, color: '#E2E2EC', fontWeight: 600 }}>{k}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>{v}</div>
                </div>
              ))}
            </div>
            <div className="lp-problem-card" style={{ textAlign: 'left' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.12em', color: '#FF4040', marginBottom: 14 }}>NEVER RECORDED</div>
              {NEVER_STORED.map(([k, v]) => (
                <div key={k} style={{ padding: '7px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ fontSize: 13, color: '#E2E2EC', fontWeight: 600 }}>{k}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Keys ───────────────────────────────────────── */}
      <section className="lp-section">
        <div className="lp-section-inner">
          <div className="lp-eyebrow">03 · Your keys</div>
          <h2 className="lp-section-h2" style={{ fontSize: 28, marginBottom: 24 }}>Two keys, two rules.</h2>
          <div className="lp-story" style={{ maxWidth: 640, margin: 0, textAlign: 'left' }}>
            <p>
              <strong>Your provider key</strong> (Anthropic, OpenAI, Gemini&hellip;) travels in the
              request header, is forwarded to the provider untouched, and is never written to a
              database, a log, or anywhere else. If we&rsquo;re breached, there is no vault of
              customer provider keys to steal — because there is no vault.
            </p>
            <p>
              <strong>Your CostWindow key</strong> (<span style={{ fontFamily: 'var(--mono)', fontSize: 14 }}>cw_live_&hellip;</span>)
              identifies your account. We store it as a SHA-256 hash — the same way passwords
              are handled. Rotate it any time from Settings.
            </p>
          </div>
        </div>
      </section>

      {/* ── Providers ──────────────────────────────────── */}
      <section className="lp-section lp-section-alt">
        <div className="lp-section-inner">
          <div className="lp-eyebrow">04 · Provider coverage</div>
          <h2 className="lp-section-h2" style={{ fontSize: 28, marginBottom: 8 }}>One proxy, the providers you actually use.</h2>
          <p className="lp-feat-body" style={{ maxWidth: 640, marginBottom: 28 }}>
            Every provider below is a base-URL change away. Most hosted-inference platforms
            speak the OpenAI wire format, so they share the same tracking path.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10, maxWidth: 900 }}>
            {PROVIDERS.map(([name, note]) => (
              <div key={name} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, padding: '12px 14px' }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#E2E2EC' }}>{name}</div>
                <div style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'var(--mono)' }}>{note}</div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 16, maxWidth: 640 }}>
            *Replicate bills by run time, not tokens — calls pass through and obey the kill
            switch, and their cost is flagged as unpriced rather than silently recorded as $0.
            Anything we can&rsquo;t price honestly says so: unpriced calls are flagged in your
            dashboard, never hidden.
          </p>
        </div>
      </section>

      {/* ── The hard stop ──────────────────────────────── */}
      <section className="lp-section">
        <div className="lp-section-inner">
          <div className="lp-eyebrow">05 · The hard stop</div>
          <h2 className="lp-section-h2" style={{ fontSize: 28, marginBottom: 24 }}>What &ldquo;blocked&rdquo; means, precisely.</h2>
          <div className="lp-story" style={{ maxWidth: 640, margin: 0, textAlign: 'left' }}>
            <p>
              <strong>Kill switch:</strong> flip a process off and its next call through the
              proxy is refused with a provider-shaped 403. It stays off until you turn it
              back on. No cooperative &ldquo;please stop&rdquo; — the request never leaves.
            </p>
            <p>
              <strong>Budgets:</strong> set a monthly cap per process, choose <em>warn</em> or{' '}
              <em>block</em>. At 100% with block, the process is disabled automatically and
              every further call is refused. Blocks lift on the 1st of the month; re-enabling
              manually clears them early. The rules are identical whether you connect by
              proxy or SDK.
            </p>
            <p>
              <strong>The June incident this was built from:</strong> an untracked agent
              drained a full provider balance overnight while every dashboard read $0.
              The control layer exists so that a process you can see is a process you can
              stop — before the provider is called, not after the bill lands.
            </p>
          </div>
        </div>
      </section>

      {/* ── Straight answers ───────────────────────────── */}
      <section className="lp-section lp-section-alt">
        <div className="lp-section-inner">
          <div className="lp-eyebrow">06 · Straight answers</div>
          <h2 className="lp-section-h2" style={{ fontSize: 28, marginBottom: 32 }}>The questions you should be asking.</h2>
          <div style={{ display: 'grid', gap: 24, maxWidth: 720 }}>
            {FAQ.map(f => (
              <div key={f.q}>
                <h3 style={{ fontSize: 16, color: '#E2E2EC', marginBottom: 8, fontWeight: 600 }}>{f.q}</h3>
                <p className="lp-feat-body" style={{ margin: 0 }}>{f.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────── */}
      <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="lp-cta-section">
          <h2 className="lp-cta-h2">Satisfied? <em>Route a call through it.</em></h2>
          <p className="lp-cta-sub">Free tier, 2 processes, no card. One environment variable to connect.</p>
          <div className="lp-cta-buttons">
            <div className="lp-cta-pill">
              <button className="lp-cta-primary" onClick={() => navigate('/register')} style={{ padding: '15px 36px', fontSize: 15, cursor: 'pointer', border: 'none' }}>
                Start free <small>2 processes · no card</small>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Footer ─────────────────────────────────────── */}
      <footer className="lp-footer">
        <span className="lp-footer-logo" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>CostWindow</span>
        <span>A product by <a href="https://myaicraft.uk">myAIcraft</a> — part of the Window family with <a href="https://radarwindow.com">RadarWindow</a></span>
        <button
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 12, fontFamily: 'var(--body)', textDecoration: 'underline' }}
          onClick={() => navigate('/login')}
        >
          Sign in
        </button>
      </footer>
    </div>
  )
}
