import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getPublicBrief } from '../api/publicApi'
import PublicShell from '../components/PublicShell'
import Markdown from '../components/Markdown'

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function PublicBrief() {
  const { slug } = useParams<{ slug: string }>()
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['public-brief', slug],
    queryFn: () => getPublicBrief(slug!),
    // Retry transient failures (e.g. a cold backend) so a brief doesn't drop to
    // a dead "not found" on the first hiccup. A real 404 is handled below.
    retry: 2,
  })

  const status = (error as { response?: { status?: number } } | null)?.response?.status
  const notFound = status === 404 || (!isLoading && !error && !data)

  return (
    <PublicShell>
      {isLoading && <p className="muted" style={{ fontSize: 13 }}>Loading…</p>}
      {!isLoading && (error || !data) && (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
            {notFound ? 'Brief not found.' : "Couldn't load this brief just now."}
          </p>
          {!notFound && (
            <button className="btn btn-ghost" style={{ marginTop: 12, fontSize: 13 }} onClick={() => refetch()}>
              Try again
            </button>
          )}
          <div style={{ marginTop: 8 }}>
            <Link to="/p" style={{ color: 'var(--green)', fontSize: 13 }}>← All briefs</Link>
          </div>
        </div>
      )}

      {data && (
        <>
          <Link to="/p" style={{ color: 'var(--text-muted)', fontSize: 12, textDecoration: 'none' }}>← All briefs</Link>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', margin: '16px 0 4px' }} className="num">{fmtDate(data.run_date)}</div>
          <Markdown md={data.content_md} />

          {data.source_health && (
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 24, fontSize: 11, color: 'var(--text-muted)', flexWrap: 'wrap' }}>
              <span style={{ textTransform: 'uppercase', letterSpacing: '0.06em' }}>Sources:</span>
              {Object.entries(data.source_health as Record<string, number>).map(([src, n]) => (
                <span key={src} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: n > 0 ? 'var(--green)' : 'var(--text-muted)', display: 'inline-block' }} />
                  {src} <span className="num">{n}</span>
                </span>
              ))}
            </div>
          )}

          <div className="card" style={{ marginTop: 40 }}>
            <p style={{ fontSize: 14, lineHeight: 1.65 }}>
              This brief was researched, scored and written autonomously, then passed through a
              three-pass quality gate. Want one for your niche?{' '}
              <Link to="/pricing" style={{ color: 'var(--green)' }}>See pricing →</Link>
            </p>
          </div>
        </>
      )}
    </PublicShell>
  )
}
