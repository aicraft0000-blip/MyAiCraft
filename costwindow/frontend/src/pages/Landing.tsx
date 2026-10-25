import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useEffect, useState } from 'react'
import './Landing.css'
import aicraftLogo from '../assets/aicraft-logo-dark.png'
import { MONTHLY_URL, YEARLY_URL } from '../billing'

// Ticking cost counter — starts at a realistic monthly total and increments
function useLiveCost(start: number, active: boolean) {
  const [cost, setCost] = useState(start)
  useEffect(() => {
    if (!active) return
    const id = setInterval(() => {
      setCost(c => parseFloat((c + Math.random() * 0.004 + 0.001).toFixed(3)))
    }, 140)
    return () => clearInterval(id)
  }, [active])
  return cost
}

// Scroll reveal hook
function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll('.reveal')
    const obs = new IntersectionObserver(
      entries => entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible') }),
      { threshold: 0.12 }
    )
    els.forEach(el => obs.observe(el))
    return () => obs.disconnect()
  }, [])
}

function Mockup() {
  const [killed, setKilled] = useState<string | null>(null)

  const rows = [
    { id: 'gpt-4o-agent',      provider: 'openai',    dot: '#1DC85E', badge: 'rgba(29,200,94,0.12)',   btext: '#1DC85E', cost: '$4.82', trend: '+38%', up: true },
    { id: 'claude-code',        provider: 'anthropic', dot: '#F0A500', badge: 'rgba(240,165,0,0.12)',   btext: '#F0A500', cost: '$2.17', trend: '+12%', up: true },
    { id: 'content-blotato',    provider: 'anthropic', dot: '#F0A500', badge: 'rgba(240,165,0,0.12)',   btext: '#F0A500', cost: '$0.44', trend: 'stable', up: false },
    { id: 'market-summariser',  provider: 'openai',    dot: '#1DC85E', badge: 'rgba(29,200,94,0.12)',   btext: '#1DC85E', cost: '$1.09', trend: '+5%',  up: true },
  ]

  return (
    <div className="lp-mockup fade-up fade-up-6">
      <div className="lp-mockup-bar">
        <span className="lp-mockup-logo">CostWindow</span>
        <div className="lp-mockup-stats">
          {[{ l: 'Today', v: '$3.21' }, { l: 'This month', v: '$71.48' }].map(s => (
            <div key={s.l}>
              <div className="lp-mockup-stat-label">{s.l}</div>
              <div className="lp-mockup-stat-val">{s.v}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="lp-mockup-alert">
        <span style={{ color: '#FF4040', fontSize: 14 }}>⚡</span>
        <span><strong>gpt-4o-agent</strong><span style={{ color: 'var(--muted)', marginLeft: 4 }}>is 3.8× above 7-day average</span></span>
      </div>

      <div className="lp-mockup-body">
        <div className="lp-mockup-section-label">API Billing</div>
        {rows.map(r => (
          <div key={r.id} className={`lp-mockup-row${killed === r.id ? ' killed' : ''}`}>
            <div className="lp-mockup-row-left">
              <div className="lp-mockup-dot" style={{ background: killed === r.id ? '#333344' : r.dot }} />
              <span className="lp-mockup-label">{r.id}</span>
              <span className="lp-mockup-badge" style={{ background: r.badge, color: r.btext }}>{r.provider}</span>
            </div>
            <div className="lp-mockup-row-right">
              <span className="lp-mockup-cost">{r.cost}</span>
              <span className={r.up ? 'lp-mockup-trend-up' : 'lp-mockup-trend-flat'}>{r.trend}</span>
              <button
                className={`lp-ks lp-ks-${killed === r.id ? 'off' : 'on'}`}
                onClick={() => setKilled(killed === r.id ? null : r.id)}
                title={killed === r.id ? 'Re-enable' : 'Kill process'}
              >
                <div className="lp-ks-thumb" />
              </button>
            </div>
          </div>
        ))}

        <div className="lp-mockup-budget">
          <div className="lp-mockup-budget-row">
            <span>gpt-4o-agent — monthly budget</span>
            <span className="lp-mockup-budget-pct">84% used</span>
          </div>
          <div className="lp-budget-bar-track">
            <div className="lp-budget-bar-fill" style={{ width: '84%' }} />
          </div>
          <div className="lp-mockup-budget-note">Auto-blocks at $20.00 · resets 1st</div>
        </div>
      </div>
    </div>
  )
}

function KillSwitchDemo() {
  const [on, setOn] = useState(true)
  return (
    <div className="lp-ks-demo-wrap">
      <div className="lp-ks-demo-label">{on ? 'Process running' : 'Process stopped'}</div>
      <button
        className={`lp-ks-large lp-ks-large-${on ? 'on' : 'off'}`}
        onClick={() => setOn(v => !v)}
      >
        <div className="lp-ks-large-thumb" />
      </button>
      <div className="lp-ks-demo-hint">
        {on ? 'Click to stop spending instantly' : 'Click to re-enable'}
      </div>
    </div>
  )
}

function CodeSnippet() {
  return (
    <div className="lp-code">
      <span className="c"># One line. No SDK. No code changes.{'\n'}</span>
      <span className="c"># Anthropic · OpenAI · Azure · Gemini · Bedrock · Groq · Mistral · xAI · Together · Fireworks · OpenRouter · DeepInfra · Perplexity{'\n'}</span>
      <span className="kw">export</span> ANTHROPIC_BASE_URL=<span className="s">"https://api.costwindow.com/proxy/anthropic/cw_live_..."</span>{'\n'}{'\n'}
      <span className="c"># Every call flows through CostWindow ↓{'\n'}</span>
      <span className="c">#   → tracked automatically (any language, any tool){'\n'}</span>
      <span className="c">#   → blocked processes refused before the provider is called{'\n'}</span>
      <span className="c">#   → your provider API key passes straight through, never stored{'\n'}</span>
      <span className="c">#   → only token counts, model &amp; cost are recorded — never your prompts or responses{'\n'}</span>{'\n'}
      <span className="c"># OpenAI? Same idea (note the /v1):{'\n'}</span>
      <span className="kw">export</span> OPENAI_BASE_URL=<span className="s">"https://api.costwindow.com/proxy/openai/cw_live_.../v1"</span>
    </div>
  )
}

function BudgetBars() {
  const bars = [
    { label: 'content-blotato',  pct: 34, color: '#1DC85E', note: '$3.40 / $10.00' },
    { label: 'gpt-4o-agent',     pct: 84, color: '#FF4040', note: '$16.80 / $20.00 — blocks at 100%' },
    { label: 'scraper-pipeline', pct: 12, color: '#1DC85E', note: '$1.20 / $10.00' },
  ]
  return (
    <div className="lp-budget-list">
      {bars.map(b => (
        <div key={b.label}>
          <div className="lp-budget-item-label">
            <span className="lp-budget-item-name">{b.label}</span>
            <span className="lp-budget-item-pct" style={{ color: b.color }}>{b.pct}%</span>
          </div>
          <div className="lp-budget-track">
            <div className="lp-budget-fill" style={{ width: `${b.pct}%`, background: b.pct > 75 ? 'linear-gradient(90deg,#F0A500,#FF4040)' : b.color }} />
          </div>
          <div className="lp-budget-note">{b.note}</div>
        </div>
      ))}
    </div>
  )
}

function RunwayTiles() {
  const tiles = [
    { label: 'Est. balance',   val: '$28.44',  sub: 'Anthropic', col: '#E2E2EC' },
    { label: 'Runway',         val: '11 days', sub: 'at current burn', col: '#FF4040' },
    { label: 'Tracked spend',  val: '$41.22',  sub: 'this month', col: '#E2E2EC' },
    { label: 'Untracked gap',  val: '⚠ $2.80', sub: 'investigate', col: '#F0A500' },
  ]
  return (
    <div className="lp-runway-grid">
      {tiles.map(t => (
        <div key={t.label} className="lp-runway-tile">
          <div className="lp-runway-tile-label">{t.label}</div>
          <div className="lp-runway-tile-val" style={{ color: t.col }}>{t.val}</div>
          <div className="lp-runway-tile-sub">{t.sub}</div>
        </div>
      ))}
    </div>
  )
}

const FEATURES = [
  {
    n: '01',
    title: 'It tells you when money leaves that nothing explains.',
    body: 'Log your real provider balance and CostWindow reconciles it against every tracked call. If spend left your account that no process accounts for, you get a tracking-gap alert — the unknown unknowns, caught. Plus runway: exactly how many days your balance lasts at current burn.',
    visual: <RunwayTiles />,
    flip: false,
  },
  {
    n: '02',
    title: 'A kill switch that refuses the call.',
    body: 'Route your calls through the CostWindow proxy and a killed process is refused before the provider is ever reached — a hard stop, not a polite request. Works on agents, cron jobs, and scripts you forgot were running. Click once. It stops.',
    visual: <KillSwitchDemo />,
    flip: true,
  },
  {
    n: '03',
    title: 'Budgets that enforce themselves.',
    body: 'Set a monthly cap per process. At 100%, the next call is blocked — no manual step, no morning-after surprise. Resets on the 1st. This is the control an autonomous agent needs and no provider console gives you.',
    visual: <BudgetBars />,
    flip: false,
  },
  {
    n: '04',
    title: 'One line to connect. The whole picture.',
    body: 'Point your base URL at CostWindow — no SDK, no code changes, any language. Claude Code and Codex sessions track via a one-command hook. And your flat subscriptions (Claude Pro, ChatGPT, tooling) — added once — sit in the same dashboard, so the number you see is your actual total AI spend.',
    visual: <CodeSnippet />,
    flip: true,
  },
]

const TICKER_ITEMS = [
  { name: 'GPT-4O-AGENT',      cost: '$4.82', trend: '↑38%', up: true },
  { name: 'CLAUDE-CODE',        cost: '$2.17', trend: '↑12%', up: true },
  { name: 'CONTENT-BLOTATO',    cost: '$0.44', trend: '—',    up: false },
  { name: 'MARKET-SUMMARISER',  cost: '$1.09', trend: '↑5%',  up: true },
  { name: 'SCRAPER-PIPELINE',   cost: '$0.31', trend: '—',    up: false },
  { name: 'HERMES-CRON',        cost: '$0.08', trend: '↓2%',  up: false },
  { name: 'RIVER-CHAT',         cost: '$0.93', trend: '↑8%',  up: true },
]

const STEPS = [
  { n: '01', title: 'Create a free account', body: 'No card, no checkout. Register, log in, and grab your API key from Settings. Two processes tracked free, every feature included.' },
  { n: '02', title: 'Point your base URL at CostWindow', body: 'One environment variable and every call — to Anthropic, OpenAI, Azure, Gemini, Bedrock, Groq and other major providers — is tracked and enforced, any language, any tool. Prefer code? The Python SDK and the one-command Claude Code hook still work.' },
  { n: '03', title: 'Set budgets. Sleep.', body: 'Every API call, CLI session, and subscription — live in one place. Cap each process monthly. Blown caps and killed processes are refused before the provider is called.' },
]

const INCLUDED = [
  'Drop-in proxy — all major AI providers, no code changes',
  'Hard kill switches & auto-block budgets',
  'Untracked spend detection',
  'Provider balance runway',
  'Python SDK — Anthropic + OpenAI',
  'Claude Code & Codex session hooks',
  'Subscriptions tracked alongside API spend',
  'Spike alerts & notifications',
]

export default function Landing() {
  const { token } = useAuth()
  const navigate  = useNavigate()
  const [counterActive, setCounterActive] = useState(true)
  const cost = useLiveCost(71.24, counterActive)
  useReveal()

  useEffect(() => {
    if (token) navigate('/dashboard', { replace: true })
  }, [token, navigate])

  const fmt = (n: number) => {
    const s = n.toFixed(2)
    return s
  }

  // Ticker content doubled for seamless loop
  const tickerContent = [...TICKER_ITEMS, ...TICKER_ITEMS]

  return (
    <div className="lp">

      {/* ── Nav ────────────────────────────────────────── */}
      <nav className="lp-nav">
        <div className="lp-nav-brand">
          <span className="lp-nav-logo">CostWindow</span>
          <div className="lp-nav-sep" />
          <a className="lp-nav-partner" href="https://myaicraft.uk" target="_blank" rel="noopener noreferrer">
            <img src={aicraftLogo} alt="AiCraft Holdings" style={{ height: 22, width: 'auto', mixBlendMode: 'screen', opacity: 0.85 }} />
          </a>
        </div>
        <div className="lp-nav-actions">
          <button className="lp-btn-ghost" onClick={() => navigate('/how-it-works')}>How it works</button>
          <button className="lp-btn-ghost" onClick={() => navigate('/login')}>Sign in</button>
          <button className="lp-btn-primary" onClick={() => navigate('/register')} style={{ cursor: 'pointer', border: 'none' }}>Start free</button>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────────── */}
      <section className="lp-hero">
        <div className="lp-hero-left">
          <div className="lp-label fade-up fade-up-1">The control layer for autonomous AI spend</div>

          <h1 className="lp-hero-h1 fade-up fade-up-2">
            Your AI is spending<br />
            <em>right now.</em>
          </h1>

          {/* Live counter */}
          <div className="lp-counter fade-up fade-up-3">
            <div className="lp-counter-row">
              <div>
                <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 6 }}>
                  API spend · this month
                </div>
                <div className="lp-counter-value">
                  <span className="currency">$ </span>{fmt(cost)}
                </div>
              </div>
              <button
                className={`lp-ks lp-ks-${counterActive ? 'on' : 'off'}`}
                onClick={() => setCounterActive(v => !v)}
                title={counterActive ? 'Stop the spend' : 'Resume'}
                style={{ transform: 'scale(1.25)', transformOrigin: 'right center' }}
              >
                <div className="lp-ks-thumb" />
              </button>
            </div>
            <div className="lp-counter-meta">
              across 6 processes &nbsp;·&nbsp;{' '}
              <span>{counterActive ? '▲ accumulating' : '◼ stopped'}</span>
            </div>
          </div>

          <p className="lp-hero-sub fade-up fade-up-4">
            Agents and cron jobs spend money while you sleep. CostWindow tracks every call,
            every CLI session, every subscription — and refuses the next call when a process
            blows its budget. A hard stop, not a dashboard you have to remember to check.
          </p>

          <div className="lp-ctas fade-up fade-up-5">
            <button className="lp-cta-primary" onClick={() => navigate('/register')} style={{ cursor: 'pointer', border: 'none' }}>
              Start free <small>2 processes · no card</small>
            </button>
            <a href={MONTHLY_URL} className="lp-cta-secondary">
              Go unlimited — £12/mo
            </a>
            <p className="lp-cta-note">
              Hosted · No servers · Cancel anytime ·{' '}
              <button onClick={() => navigate('/login')}>Already a customer?</button>
            </p>
          </div>
        </div>

        <div className="lp-hero-right">
          <Mockup />
        </div>
      </section>

      {/* ── Ticker ─────────────────────────────────────── */}
      <div className="lp-ticker-wrap">
        <div className="lp-ticker">
          {tickerContent.map((item, i) => (
            <div key={i} className="lp-ticker-item">
              <span className="lp-ticker-name">{item.name}</span>
              <span className="lp-ticker-cost">{item.cost}</span>
              <span className={item.up ? 'lp-ticker-up' : 'lp-ticker-flat'}>{item.trend}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── The incident ───────────────────────────────── */}
      <section className="lp-section">
        <div className="lp-section-inner lp-section-center reveal">
          <div className="lp-eyebrow">Why this exists</div>
          <h2 className="lp-section-h2" style={{ marginBottom: 48 }}>
            One agent. One night. <em>The whole balance.</em>
          </h2>
          <div className="lp-story">
            <p>
              In June, an autonomous agent on this account quietly spent{' '}
              <span className="lp-story-figure">$29</span> in about thirty hours.
              The cost dashboard showed <span className="lp-story-figure">$0</span> —
              the agent wasn't wired into anything, so to every tool watching, it didn't exist.
            </p>
            <p>
              By morning the provider balance had drained to zero and every scheduled job
              on the account was failing with <em>"credit balance too low."</em> The audit
              took two days. The agent had been visible the whole time — in the one place
              nothing was looking.
            </p>
            <p>
              CostWindow's control layer was built from that night: balance reconciliation
              that flags spend nothing explains, budgets wired to a switch that actually
              refuses the next call, and a proxy so nothing can spend invisibly again.
            </p>
          </div>
        </div>
      </section>

      {/* ── Problem ────────────────────────────────────── */}
      <section className="lp-section lp-section-alt">
        <div className="lp-section-inner lp-section-center reveal">
          <div className="lp-eyebrow">The problem</div>
          <h2 className="lp-section-h2">
            AI spending is <em>invisible</em><br />until the bill arrives.
          </h2>
          <p className="lp-section-lead" style={{ maxWidth: 500, margin: '0 auto 48px' }}>
            No single tool sees your full picture. By the time you notice, it's already happened.
          </p>
          <div className="lp-problem-grid">
            {[
              { n: '1', icon: '📈', title: 'API bills spike overnight', body: 'One runaway script or misconfigured agent. You find out the next morning when you check Anthropic\'s console — if you remember to check.' },
              { n: '2', icon: '👻', title: 'Subscriptions compound unseen', body: 'Claude Pro, ChatGPT Plus, Blotato, OpusClip. Each reasonable in isolation. Together, unchecked, quietly adding up every month.' },
              { n: '3', icon: '🧩', title: 'There is no total', body: 'Your AI spend is split across Anthropic\'s console, OpenAI\'s dashboard, and a dozen Stripe receipts. No combined view exists. No kill switch either.' },
            ].map(p => (
              <div key={p.n} className="lp-problem-card">
                <div className="lp-problem-num">{p.n}</div>
                <div className="lp-problem-icon">{p.icon}</div>
                <h3 className="lp-problem-h3">{p.title}</h3>
                <p className="lp-problem-body">{p.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ───────────────────────────────────── */}
      <section className="lp-section">
        <div className="lp-section-inner">
          <div className="lp-section-center reveal" style={{ marginBottom: 56 }}>
            <div className="lp-eyebrow">What CostWindow does</div>
            <h2 className="lp-section-h2">
              Every tool. Every call. <em>Every penny.</em>
            </h2>
          </div>
          <div className="lp-features">
            {FEATURES.map(f => (
              <div key={f.n} className={`lp-feat reveal${f.flip ? ' lp-feat-flip' : ''}`}>
                <div className="lp-feat-text">
                  <div className="lp-feat-n">{f.n}</div>
                  <h3 className="lp-feat-h3">{f.title}</h3>
                  <p className="lp-feat-body">{f.body}</p>
                </div>
                <div className="lp-feat-visual">
                  {f.visual}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ───────────────────────────────── */}
      <section className="lp-section lp-section-alt">
        <div className="lp-section-inner lp-section-center reveal">
          <div className="lp-eyebrow">Setup in minutes</div>
          <h2 className="lp-section-h2" style={{ marginBottom: 64 }}>How it works</h2>
          <div className="lp-steps">
            {STEPS.map(s => (
              <div key={s.n} className="lp-step" style={{ textAlign: 'left' }}>
                <div className="lp-step-num">{s.n}</div>
                <h3 className="lp-step-h3">{s.title}</h3>
                <p className="lp-step-body">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ────────────────────────────────────── */}
      <section className="lp-section lp-section-center">
        <div className="lp-section-inner reveal">
          <div className="lp-eyebrow">Pricing</div>
          <h2 className="lp-section-h2" style={{ marginBottom: 12 }}>Simple, honest pricing.</h2>
          <p style={{ color: 'var(--muted)', fontSize: 15, marginBottom: 52 }}>
            Every feature on every plan. Paid lifts the process cap. No seat limits.
          </p>
          <div className="lp-pricing-grid">
            {/* Free */}
            <div className="lp-plan">
              <div className="lp-plan-period">Free</div>
              <div className="lp-plan-price"><sup>£</sup>0</div>
              <div className="lp-plan-desc">2 processes · every feature · no card</div>
              <div style={{ marginBottom: 32 }} />
              <button className="lp-plan-btn lp-plan-btn-ghost" onClick={() => navigate('/register')} style={{ cursor: 'pointer', width: '100%' }}>Start free</button>
            </div>
            {/* Monthly */}
            <div className="lp-plan">
              <div className="lp-plan-period">Monthly</div>
              <div className="lp-plan-price"><sup>£</sup>12</div>
              <div className="lp-plan-desc">unlimited processes · cancel anytime</div>
              <div style={{ marginBottom: 32 }} />
              <a href={MONTHLY_URL} className="lp-plan-btn lp-plan-btn-ghost">Start Monthly</a>
            </div>
            {/* Yearly */}
            <div className="lp-plan lp-plan-featured">
              <div className="lp-plan-badge">Best value</div>
              <div className="lp-plan-period">Yearly</div>
              <div className="lp-plan-price"><sup>£</sup>99</div>
              <div className="lp-plan-desc">unlimited · that's £8.25/mo</div>
              <div className="lp-plan-save">Save £45 vs monthly</div>
              <a href={YEARLY_URL} className="lp-plan-btn lp-plan-btn-amber">Start Yearly</a>
            </div>
          </div>
          <div className="lp-feat-list">
            {INCLUDED.map(f => (
              <div key={f} className="lp-feat-item">
                <span className="lp-feat-check">✓</span>
                {f}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ──────────────────────────────────── */}
      <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="lp-cta-section reveal">
          <h2 className="lp-cta-h2">
            Stop finding out about<br />
            AI costs <em>after the fact.</em>
          </h2>
          <p className="lp-cta-sub">
            Every surprise bill you've had could have been caught — or refused — before it hit.
          </p>
          <div className="lp-cta-buttons">
            <div className="lp-cta-pill">
              <button className="lp-cta-primary" onClick={() => navigate('/register')} style={{ padding: '15px 36px', fontSize: 15, cursor: 'pointer', border: 'none' }}>
                Start free <small>2 processes · no card</small>
              </button>
              <span className="lp-cta-pill-note lp-cta-pill-note-amber">Every feature included</span>
            </div>
            <div className="lp-cta-pill">
              <a href={YEARLY_URL} className="lp-cta-secondary" style={{ padding: '15px 36px', fontSize: 15 }}>
                Go unlimited — £99/yr
              </a>
              <span className="lp-cta-pill-note">or £12/mo · cancel anytime</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Footer ─────────────────────────────────────── */}
      <footer className="lp-footer">
        <span className="lp-footer-logo">CostWindow</span>
        <span>A product by <a href="https://myaicraft.uk">myAIcraft</a> — part of the Window family with <a href="https://radarwindow.com">RadarWindow</a></span>
        <button
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 12, fontFamily: 'var(--body)', textDecoration: 'underline' }}
          onClick={() => navigate('/how-it-works')}
        >
          How it works &amp; security
        </button>
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
