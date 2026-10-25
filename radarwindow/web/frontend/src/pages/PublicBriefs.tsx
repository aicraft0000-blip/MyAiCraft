import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { listPublicBriefs } from '../api/publicApi'
import PublicShell from '../components/PublicShell'

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function PublicBriefs() {
  const { data: briefs, isLoading, error } = useQuery({ queryKey: ['public-briefs'], queryFn: listPublicBriefs })

  return (
    <PublicShell>
      <div className="page-title">
        The weekly intelligence brief
        <p className="page-sub">
          Researched from live signals across Reddit, Hacker News, GitHub, prediction markets and news —
          velocity-scored, written in the niche's own vocabulary, and passed through a three-pass quality gate.
        </p>
      </div>

      {isLoading && <p className="muted" style={{ fontSize: 13 }}>Loading…</p>}
      {error    && <p className="error-msg">Failed to load briefs.</p>}

      {briefs && briefs.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>No public briefs yet — the first one lands soon.</p>
        </div>
      )}

      {briefs && briefs.map((b: any) => (
        <Link key={b.slug} to={`/p/${b.slug}`} className="card"
          style={{ display: 'block', marginBottom: 12, textDecoration: 'none' }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }} className="num">{fmtDate(b.run_date)}</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-h)', marginBottom: 8 }}>{b.title}</div>
          <p style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.6 }}>{b.excerpt}</p>
          <span style={{ display: 'inline-block', marginTop: 10, fontSize: 12, color: 'var(--green)' }}>Read the brief →</span>
        </Link>
      ))}
    </PublicShell>
  )
}
