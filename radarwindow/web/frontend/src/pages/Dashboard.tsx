import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { listBriefs } from '../api/briefs'
import { listDigests } from '../api/digests'
import { listNiches, Niche } from '../api/niches'
import { latestQa } from '../api/qa'
import BriefsTable from '../components/BriefsTable'
import DigestList from '../components/DigestList'

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

// The Dashboard is the desk: it only shows briefs that still need the owner —
// drafts awaiting review and approved ones queued to publish. Posted and
// archived briefs move to the Archive page, as do signal sweeps older
// than the recency window.
const NEEDS_ACTION = ['draft', 'approved']
export const DIGEST_DAYS = 5

const csv = (v?: string) => (v || '').split(',').map(s => s.trim()).filter(Boolean)

function feedHost(url: string) {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url }
}

function SourceGroup({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
        {title}
      </div>
      <div>{items.map(i => <span key={i} className="chip">{i}</span>)}</div>
    </div>
  )
}

function NicheSources({ niche, lastSweep }: { niche: Niche; lastSweep?: Record<string, number> }) {
  return (
    <div style={{ paddingBottom: 14, marginBottom: 14, borderBottom: '1px solid var(--border)' }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-h)', marginBottom: 8 }}>{niche.label}</div>
      <SourceGroup title="Subreddits" items={csv(niche.subreddits).map(s => `r/${s}`)} />
      <SourceGroup title="GitHub topics" items={csv(niche.github_topics).map(t => `#${t}`)} />
      <SourceGroup title="Web searches" items={csv(niche.web_queries).map(q => `“${q}”`)} />
      <SourceGroup title="Your feeds" items={csv(niche.rss_feeds).map(feedHost)} />
      <p className="muted" style={{ fontSize: 11, margin: '4px 0 0' }}>+ Hacker News &amp; Polymarket, always on — filtered to your niche</p>
      {lastSweep && (
        <p className="muted" style={{ fontSize: 11, marginTop: 6 }}>
          Last sweep: {Object.entries(lastSweep).map(([k, v]) => `${k} ${v}`).join(' · ')}
        </p>
      )}
    </div>
  )
}

// Confirmation that the recurring self-QA (weekly alignment check) ran:
// what it auto-fixed, what needs a human, and how on-niche the digests are.
function QaBanner() {
  const { data: reports } = useQuery({ queryKey: ['qa'], queryFn: latestQa })
  if (!reports || !reports.length) return null

  const last = reports[0].created_at
  const needsAttention = reports.some(r => r.status === 'attention')
  const autoFixed = reports.reduce((n, r) => n + r.findings.filter(f => f.auto_fixed).length, 0)
  const open = reports.flatMap(r =>
    r.findings.filter(f => !f.auto_fixed).map(f => ({ label: r.niche_label, msg: f.message })))

  return (
    <div className="card" style={{
      marginBottom: 20, padding: '12px 16px',
      borderLeft: `3px solid ${needsAttention ? '#d97706' : 'var(--green)'}`,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-h)' }}>
          Self-QA ran {fmtDate(last)}
        </span>
        <span style={{ fontSize: 12, color: needsAttention ? '#d97706' : 'var(--green)', fontWeight: 600 }}>
          {needsAttention
            ? `${open.length} finding${open.length !== 1 ? 's' : ''} need${open.length === 1 ? 's' : ''} your eye`
            : 'all niches aligned'}
          {autoFixed > 0 && ` · ${autoFixed} setting${autoFixed !== 1 ? 's' : ''} auto-fixed`}
        </span>
      </div>
      <div style={{ marginTop: 6 }}>
        {reports.map(r => (
          <p key={r.id} className="muted" style={{ fontSize: 12, margin: '2px 0' }}>
            <strong style={{ color: 'var(--text-h)' }}>{r.niche_label}</strong>: {r.summary}
            {r.on_niche_pct != null && ` (${Math.round(r.on_niche_pct * 100)}% of digest on-niche)`}
          </p>
        ))}
        {open.map((f, i) => (
          <p key={i} style={{ fontSize: 12, margin: '4px 0 0', color: '#d97706' }}>
            ⚠ {f.label}: {f.msg} — <Link to="/niches" style={{ color: '#d97706', fontWeight: 600 }}>fix in Niches</Link>
          </p>
        ))}
      </div>
    </div>
  )
}

function SourcesPanel() {
  const { data: niches } = useQuery({ queryKey: ['niches'], queryFn: listNiches })
  const { data: digests } = useQuery({ queryKey: ['digests'], queryFn: listDigests })

  const active = (niches || []).filter(n => n.active)
  if (!active.length) return null

  // Most recent digest per niche → that niche's "last sweep" source counts
  const sweeps: Record<string, Record<string, number>> = {}
  for (const d of digests || []) {
    if (d.niche_id && d.source_health && !sweeps[d.niche_id]) sweeps[d.niche_id] = d.source_health
  }

  return (
    <div className="card sources-panel">
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 14 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-h)' }}>Sources in play</div>
        <Link to="/niches" style={{ fontSize: 12, color: 'var(--green)', fontWeight: 600 }}>Manage →</Link>
      </div>
      {active.map(n => <NicheSources key={n.id} niche={n} lastSweep={sweeps[n.id]} />)}
      <p className="muted" style={{ fontSize: 11, margin: 0 }}>
        These only change when you change them — the signals change daily, the places we look don't.
      </p>
    </div>
  )
}

export default function Dashboard() {
  const { data: briefs, isLoading, error } = useQuery({ queryKey: ['briefs'], queryFn: listBriefs })
  const { data: digests } = useQuery({ queryKey: ['digests'], queryFn: listDigests })

  const active = (briefs || []).filter((b: any) => NEEDS_ACTION.includes(b.status))
  const doneCount = (briefs || []).length - active.length
  const cutoff = Date.now() - DIGEST_DAYS * 86_400_000
  const recentDigests = (digests || []).filter((d: any) => new Date(d.run_date).getTime() >= cutoff)

  return (
    <div className="dash-grid">
      <div>
        <QaBanner />
        <div className="page-title" style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <span>
            Briefs needing your attention
            <p className="page-sub">Drafts waiting for review and approved briefs queued to publish. Actioned briefs live in the Archive.</p>
          </span>
          {doneCount > 0 && (
            <Link to="/archive" style={{ fontSize: 13, color: 'var(--green)', fontWeight: 600, whiteSpace: 'nowrap' }}>
              Archive ({doneCount}) →
            </Link>
          )}
        </div>

        {isLoading && <p className="muted" style={{ fontSize: 13 }}>Loading…</p>}
        {error    && <p className="error-msg">Failed to load briefs.</p>}

        {briefs && active.length === 0 && (
          <div className="card" style={{ textAlign: 'center', padding: 48 }}>
            <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
              {briefs.length === 0 ? 'No briefs yet.' : 'All caught up — nothing needs your attention.'}
            </p>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 8 }}>
              {briefs.length === 0
                ? "The weekly brief is written Monday 07:00. You'll get an email the moment it's ready to read."
                : 'The weekly brief arrives Monday 07:00, or make one from a daily signal below. Past briefs are in the Archive.'}
            </p>
          </div>
        )}

        {active.length > 0 && <BriefsTable briefs={active} />}

        {recentDigests.length > 0 && (
          <div style={{ marginTop: 36 }}>
            <div className="page-title" style={{ fontSize: 16, marginBottom: 12, display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
              <span>
                Daily signals
                <p className="page-sub">Raw radar output, velocity-scored — the last 5 days. Older sweeps are in the Archive.</p>
              </span>
            </div>
            <DigestList digests={recentDigests} />
          </div>
        )}
      </div>

      <SourcesPanel />
    </div>
  )
}
