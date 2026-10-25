import { Link } from 'react-router-dom'
import PublicShell from '../components/PublicShell'

// The methodology page. Every claim here is written from the pipeline source
// (scoring.py, synthesis.py, main.py) — if the code changes, change this page.

const SOURCES = [
  ['Reddit', 'niche subreddits you configure — discussion, where the pain points live'],
  ['Hacker News', 'front page + search, engagement-scored'],
  ['GitHub', 'repos in your topics — what builders are adopting'],
  ['Polymarket', 'prediction markets — where money disagrees with headlines'],
  ['Live web search', 'news queries built from your niche'],
]

const CRITIQUE_CHECKS = [
  ['Anti-slop', 'no filler, no hype vocabulary, none of the tells that mark text as machine-written'],
  ['Niche vocabulary', 'reads like an insider in your world wrote it — not a marketer writing about your world'],
  ['Specificity', 'every claim grounded in this week’s actual signal data, not general knowledge'],
  ['Structure', 'no formula writing — no three-item lists, no rhetorical-question-then-answer'],
]

const NOT_DONE = [
  ['No single-pass output, ever', 'Every brief goes through the full gate. There is no fast path.'],
  ['No stock imagery', 'Images are generated from this week’s specific signal, only after the text has passed the gate. A generic "futuristic tech background" is a failure condition.'],
  ['No forced content in thin weeks', 'A weak sweep produces a shorter, narrower brief — not padded filler pretending to be insight.'],
  ['No custody of your accounts', 'Posting is optional and handled by a posting app you connect. RadarWindow never holds your social logins or tokens.'],
]

function SectionTitle({ n, children }: { n: string; children: React.ReactNode }) {
  return (
    <div style={{ margin: '40px 0 14px', display: 'flex', alignItems: 'baseline', gap: 10 }}>
      <span className="num" style={{ fontSize: 12, color: 'var(--green)', fontWeight: 600 }}>{n}</span>
      <h2 style={{ fontSize: 19, color: 'var(--text-h)', fontWeight: 700 }}>{children}</h2>
    </div>
  )
}

export default function Methodology() {
  return (
    <PublicShell>
      <div className="page-title" style={{ textAlign: 'center' }}>
        Methodology
        <p className="page-sub">
          How a brief gets made — the sources, the scoring math, and the gate.
          Written from the pipeline source code, not the marketing copy.
        </p>
      </div>

      {/* ── Daily vs weekly ─────────────────────────── */}
      <SectionTitle n="01">Two deliverables, two different jobs</SectionTitle>
      <p style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--text)' }}>
        RadarWindow sends you two different things, and they are not the same product
        at two speeds.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 14, marginTop: 14 }}>
        <div className="card">
          <div style={{ fontSize: 11, fontFamily: 'var(--mono, monospace)', letterSpacing: '0.08em', color: 'var(--text-muted)', marginBottom: 8 }}>
            DAILY · 07:00 · THE FEED
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-h)', marginBottom: 8 }}>Signal digest</div>
          <p style={{ fontSize: 13, lineHeight: 1.65, color: 'var(--text)' }}>
            A radar sweep and a ranking — <strong>no AI writing at all</strong>. The top
            signals in your niche land in your inbox and on your dashboard, scored and
            sorted. It exists because a weekly cadence would miss things that rise and
            peak inside a week. Each signal carries a one-click &ldquo;make this a
            brief&rdquo; switch.
          </p>
        </div>
        <div className="card" style={{ borderColor: 'var(--green-border)' }}>
          <div style={{ fontSize: 11, fontFamily: 'var(--mono, monospace)', letterSpacing: '0.08em', color: 'var(--green)', marginBottom: 8 }}>
            WEEKLY · MONDAY · THE PRODUCT
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-h)', marginBottom: 8 }}>The gated brief</div>
          <p style={{ fontSize: 13, lineHeight: 1.65, color: 'var(--text)' }}>
            One story, fully worked: researched from the week&rsquo;s scored signals,
            written as an analyst brief, run through the three-pass quality gate, and
            delivered with the media kit — a post per platform, imagery, audio, reel —
            all derived from the brief.
          </p>
        </div>
      </div>

      {/* ── The sweep ───────────────────────────────── */}
      <SectionTitle n="02">The sweep</SectionTitle>
      <p style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--text)', marginBottom: 12 }}>
        Five kinds of source, fetched concurrently. Reddit, GitHub and web queries are
        driven by <em>your</em> saved niche and sources; Hacker News and Polymarket are
        watched for everyone. A source that fails never blocks the sweep — it&rsquo;s
        recorded in the source-health report instead, so you can see exactly what this
        week&rsquo;s brief was and wasn&rsquo;t built from.
      </p>
      <p style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--text)', marginBottom: 12 }}>
        This isn&rsquo;t tech-only. The niche and its sources are yours to set, and the
        source suggester has been tested on worlds as far from software as specialty
        coffee roasting and family law — it returns their real communities and search
        queries, not generic news. The honest constraint: <strong>discussion-rich
        niches give the sharpest signal.</strong> A niche with living subreddits,
        forums, and search chatter produces a dense sweep; a niche nobody discusses in
        public produces a thinner one — and the source-health report will show you
        that plainly rather than pad the gap with filler.
      </p>
      <div className="card">
        {SOURCES.map(([name, note]) => (
          <div key={name} style={{ display: 'flex', gap: 12, padding: '7px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
            <span style={{ minWidth: 110, fontWeight: 600, color: 'var(--text-h)' }}>{name}</span>
            <span style={{ color: 'var(--text)', lineHeight: 1.5 }}>{note}</span>
          </div>
        ))}
      </div>

      {/* ── Scoring ─────────────────────────────────── */}
      <SectionTitle n="03">The scoring math, honestly</SectionTitle>
      <div style={{ fontSize: 14, lineHeight: 1.75, color: 'var(--text)' }}>
        <p style={{ marginBottom: 10 }}>
          Every signal gets a combined score: <strong>60% volume</strong> (how much
          engagement it has) and <strong>40% velocity</strong> (how fast it&rsquo;s
          accumulating that engagement, with old items scoring zero). Velocity is the
          part that matters — it&rsquo;s the difference between what&rsquo;s{' '}
          <em>rising</em> and what already peaked.
        </p>
        <p style={{ marginBottom: 10 }}>
          Two details keep the ranking honest. Scores are normalised <em>within each
          source first</em>, so a 50-star repo that&rsquo;s moving can outrank a
          50,000-star one that isn&rsquo;t, and Reddit can&rsquo;t drown out Polymarket
          just by being louder. Then discussion sources (Reddit, Hacker News — where
          pain points surface) are weighted up, and cumulative ones (GitHub stars,
          which only ever go up) are weighted down.
        </p>
        <p>
          A sweep typically scores 60+ signals. That number is the size of the haystack,
          not the deliverable — <strong>the ranking is the curation</strong>. Your digest
          shows the top of the list; the rest exist so you can trust that the top ten
          beat sixty others, not that they were the only ten found.
        </p>
      </div>

      {/* ── The gate ────────────────────────────────── */}
      <SectionTitle n="04">The three-pass gate</SectionTitle>
      <p style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--text)', marginBottom: 12 }}>
        No brief is ever single-pass. The pipeline <strong>generates</strong> the brief
        and its platform posts, then a separate <strong>critique</strong> pass scores
        the draft against four checks, then a <strong>revise</strong> pass rewrites
        against that critique — up to two revisions before the best attempt ships.
        The critique score and revision count are recorded on every brief.
      </p>
      <div className="card">
        {CRITIQUE_CHECKS.map(([name, note]) => (
          <div key={name} style={{ display: 'flex', gap: 12, padding: '7px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
            <span style={{ minWidth: 130, fontWeight: 600, color: 'var(--text-h)' }}>{name}</span>
            <span style={{ color: 'var(--text)', lineHeight: 1.5 }}>{note}</span>
          </div>
        ))}
      </div>
      <p style={{ fontSize: 13, lineHeight: 1.65, color: 'var(--text-muted)', marginTop: 10 }}>
        Content with editorial oversight performs 4.1× better than raw automated output.
        The gate is that oversight, in code, on every brief.
      </p>

      {/* ── Receipts ────────────────────────────────── */}
      <SectionTitle n="05">The receipts</SectionTitle>
      <p style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--text)' }}>
        Every media kit ships with <span className="num">signals.json</span> — the raw
        scored signals the brief was built from — and{' '}
        <span className="num">source-health.md</span>, which says which sources
        delivered this week and which didn&rsquo;t. You never have to take a
        brief&rsquo;s word for where it came from. The{' '}
        <Link to="/p" style={{ color: 'var(--green)' }}>public briefs</Link> are
        unedited pipeline output — read them as the proof, not a demo.
      </p>

      {/* ── What it refuses to do ───────────────────── */}
      <SectionTitle n="06">What it refuses to do</SectionTitle>
      <div style={{ display: 'grid', gap: 10 }}>
        {NOT_DONE.map(([name, note]) => (
          <div key={name} className="card" style={{ padding: '12px 16px' }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-h)', marginBottom: 4 }}>{name}</div>
            <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.6 }}>{note}</div>
          </div>
        ))}
      </div>

      {/* ── CTA ─────────────────────────────────────── */}
      <div style={{ textAlign: 'center', marginTop: 48 }}>
        <p style={{ fontSize: 14, color: 'var(--text)', marginBottom: 16 }}>
          The fastest way to judge the methodology is to read what it produces.
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link to="/p" className="btn btn-primary">Read the briefs — free</Link>
          <Link to="/pricing" className="btn btn-ghost">Point it at your niche</Link>
        </div>
      </div>
    </PublicShell>
  )
}
