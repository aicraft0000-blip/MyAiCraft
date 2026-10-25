import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { listPublicBriefs } from '../api/publicApi'
import './Landing.css'

// "The Signals Desk, 03:00" — a night-shift intelligence station.
// The console (dark, mono telemetry, radar sweep) produces the document
// (light briefing paper, serif, stamped). That relationship IS the product.

type PublicBrief = { slug: string; title: string; run_date: string; excerpt: string }

function useUtcClock() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return now.toISOString().slice(0, 19).replace('T', ' ') + 'Z'
}

function Radar() {
  return (
    <div className="sd-radar" aria-hidden="true">
      <div className="sd-radar-ring r1" />
      <div className="sd-radar-ring r2" />
      <div className="sd-radar-ring r3" />
      <div className="sd-radar-grid" />
      <div className="sd-radar-sweep" />
      <div className="sd-blip b1" />
      <div className="sd-blip b2" />
      <div className="sd-blip b3" />
    </div>
  )
}

const STEPS = [
  {
    n: '01',
    tag: 'SET',
    title: 'Tell it your niche',
    body: 'Skateboarding. Specialty coffee roasting. Family law. "MCP servers for fintech". As broad or as tight as your world actually runs — RadarWindow aims a scraper at its highest-volume sources and watches them around the clock.',
  },
  {
    n: '02',
    tag: 'SCORE',
    title: 'Three scores, not one',
    body: "Every signal is rated on engagement, on recommendations, and on velocity — how fast it's being shared. You get the ones that top all three.",
  },
  {
    n: '03',
    tag: 'SIGNAL',
    title: "Ahead before you've looked",
    body: 'A short signal digest lands daily — the top signals in your inbox and on your dashboard, ranked. The front edge of your niche, delivered. Once a week, the one you pick becomes the full gated brief.',
  },
  {
    n: '04',
    tag: 'CHOOSE',
    title: "Pick what's worth sharing",
    body: 'Read the signals. See one you want to post about? Flip a switch and RadarWindow writes it up — as briefs shaped for the exact platforms you post on.',
  },
  {
    n: '05',
    tag: 'GATE',
    title: 'Three passes, no AI tells',
    body: 'Every brief runs a three-pass gate — generate, critique, revise — tuned to strip jargon and AI tells so it reads like you wrote it, not a bot.',
  },
  {
    n: '06',
    tag: 'SHIP',
    title: 'One story, a post per account',
    body: 'You get one final brief of the story you want to tell, plus a post derived from it for each account. Approve them and post yourself — or connect a posting app like Blotato and let it publish for you.',
  },
]

const KIT_FILES: Array<[string, string]> = [
  ['brief.md', 'the analyst brief — the product'],
  ['x-post.md + x-image.jpg', 'ready for X'],
  ['linkedin-post.md + linkedin-image.jpg', 'ready for LinkedIn'],
  ['instagram-post.md + instagram-reel.mp4', '15s reel, mood-matched track'],
  ['signals.json + source-health.md', 'the receipts'],
]

export default function Landing() {
  const clock = useUtcClock()
  const { data: briefs } = useQuery<PublicBrief[]>({
    queryKey: ['public-briefs'],
    queryFn: listPublicBriefs,
    staleTime: 5 * 60 * 1000,
  })
  const latest = briefs?.[0]

  return (
    <div className="sd">
      {/* ── Classification strip ─────────────────── */}
      <div className="sd-strip">
        <span>RADARWINDOW · AUTONOMOUS INTELLIGENCE · QUALITY-GATED</span>
        <span className="sd-strip-clock">{clock}</span>
      </div>

      {/* ── Nav ──────────────────────────────────── */}
      <header className="sd-nav">
        <Link to="/" className="sd-wordmark">RADAR<span>WINDOW</span></Link>
        <nav>
          <Link to="/p">Briefs</Link>
          <Link to="/methodology">Methodology</Link>
          <Link to="/pricing">Pricing</Link>
          <Link to="/login" className="sd-btn sd-btn-ghost sd-btn-sm">Sign in</Link>
        </nav>
      </header>

      {/* ── Hero: the console and the document ───── */}
      <section className="sd-hero">
        <Radar />
        <div className="sd-hero-inner">
          <div className="sd-hero-text">
            <div className="sd-eyebrow">The signals desk</div>
            <h1>
              The weekly analyst brief for <em>your</em> niche.
            </h1>
            <p className="sd-hero-sub">
              Tell RadarWindow your niche. It watches the highest-volume sources, ranks
              what's <strong>rising</strong> — not what already peaked — and hands you the
              signals worth knowing. Turn any of them into a polished brief and a ready
              post for every platform, in your voice, through a quality gate that kills the
              AI tells. Post it yourself, or let it publish for you.
            </p>
            <div className="sd-ctas">
              <Link to="/pricing" className="sd-btn sd-btn-primary">Point the radar at your world</Link>
              <Link to="/p" className="sd-btn sd-btn-ghost">Read the briefs — free</Link>
            </div>
            <div className="sd-telemetry">
              5 SOURCES · 60+ SIGNALS SCORED, YOU SEE THE TOP · 3-PASS GATE · DAILY DIGEST + WEEKLY GATED BRIEF
            </div>
          </div>

          {/* The document artifact — live latest brief as briefing paper */}
          {latest && (
            <Link to={`/p/${latest.slug}`} className="sd-paper" title="Read the full brief">
              <div className="sd-paper-head">
                <span>INTELLIGENCE BRIEF</span>
                <span>{latest.run_date.slice(0, 10)}</span>
              </div>
              <div className="sd-paper-rule" />
              <h2>{latest.title}</h2>
              <p>{latest.excerpt}</p>
              <div className="sd-paper-foot">
                <span className="sd-stamp">PASSED QUALITY GATE · 3 PASSES</span>
                <span className="sd-paper-dist">DIST: SUBSCRIBERS + PUBLIC</span>
              </div>
              <div className="sd-paper-cta">Read the full brief →</div>
            </Link>
          )}
        </div>
      </section>

      {/* ── Provenance line ──────────────────────── */}
      {latest && (
        <div className="sd-provenance">
          The document above was researched, scored, written and revised{' '}
          <strong>autonomously</strong> on {latest.run_date.slice(0, 10)}. No human touched it.
        </div>
      )}

      {/* ── How a brief gets made ────────────────── */}
      <section className="sd-section sd-steps-section">
        <div className="sd-eyebrow">How it works — from your niche to posted</div>
        <div className="sd-steps">
          {STEPS.map(s => (
            <div key={s.n} className="sd-step">
              <div className="sd-step-head">
                <span className="sd-step-n">{s.n}</span>
                <span className="sd-step-tag">{s.tag}</span>
              </div>
              <h3>{s.title}</h3>
              <p>{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── The standard: two slips ──────────────── */}
      <section className="sd-section">
        <div className="sd-eyebrow">The standard the gate enforces</div>
        <div className="sd-slips">
          <div className="sd-slip sd-slip-rejected">
            <div className="sd-slip-stamp">REJECTED — PASS 2</div>
            <p>"Unlock the transformative power of AI and take your content journey to the next level!"</p>
          </div>
          <div className="sd-slip sd-slip-cleared">
            <div className="sd-slip-stamp">CLEARED TO SHIP</div>
            <p>"Anthropic cut input pricing 40% this week. What cost £8/M tokens now costs £4.80. Your eval budget just doubled itself."</p>
          </div>
        </div>
        <p className="sd-aside">
          Content with editorial oversight performs 4.1× better than raw automated output.
          The gate is that oversight — in code, on every brief, every week.
        </p>
      </section>

      {/* ── The kit ──────────────────────────────── */}
      <section className="sd-section">
        <div className="sd-eyebrow">Subscribers download the kit</div>
        <div className="sd-kit-grid">
          <div className="sd-kit">
            <div className="sd-kit-root">radarwindow-brief-{latest ? latest.run_date.slice(0, 10) : '2026-07-05'}/</div>
            {KIT_FILES.map(([f, note]) => (
              <div key={f} className="sd-kit-row">
                <span>├── {f}</span>
                <span>{note}</span>
              </div>
            ))}
          </div>
          <div className="sd-kit-text">
            <h3>The brief is the product.<br />Everything else is derived from it.</h3>
            <p>
              Platform drafts written from the brief's own analysis. Imagery generated from
              this week's actual signal — never a stock "futuristic tech background". A
              15-second reel with a track matched to the signal's mood. Post it yourself,
              feed it to your scheduler, or connect posting and let it run.
            </p>
            <p className="sd-kit-note">WEEKLY · IN YOUR INBOX · BEFORE YOU'RE AT YOUR DESK</p>
          </div>
        </div>
      </section>

      {/* ── Final CTA: the press run ─────────────── */}
      <section className="sd-final">
        <div className="sd-final-inner">
          <h2>Read free. Or point the radar at your world.</h2>
          <p className="sd-final-tiers">
            READER — free, every week &nbsp;·&nbsp; RADAR — £29/mo, your niche + the kit
            &nbsp;·&nbsp; RADAR PRO — £79/mo, + competitor gap and connected posting
          </p>
          <div className="sd-ctas sd-ctas-center">
            <Link to="/pricing" className="sd-btn sd-btn-primary">See pricing</Link>
            <Link to="/p" className="sd-btn sd-btn-paper">Read the briefs first</Link>
          </div>
        </div>
      </section>

      <footer className="sd-footer">
        <span className="sd-wordmark sd-wordmark-sm">RADAR<span>WINDOW</span></span>
        <span>
          A product by <a href="https://myaicraft.uk">myAIcraft</a> — part of the Window
          family with <a href="https://costwindow.com">CostWindow</a>
        </span>
        <Link to="/login">Sign in</Link>
      </footer>
    </div>
  )
}
