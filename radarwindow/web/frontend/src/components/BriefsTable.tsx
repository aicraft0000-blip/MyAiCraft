import { Link } from 'react-router-dom'

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>
}

function MoodDot({ mood }: { mood: string }) {
  const colors: Record<string, string> = {
    rising: 'var(--green)', bullish: 'var(--green)', cautionary: 'var(--amber)', neutral: 'var(--text-muted)',
  }
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12, color: 'var(--text-muted)' }}>
      <span style={{ width: 7, height: 7, borderRadius: '50%', background: colors[mood] || 'var(--text-muted)', display: 'inline-block' }} />
      {mood}
    </span>
  )
}

export default function BriefsTable({ briefs }: { briefs: any[] }) {
  return (
    <div className="card table-scroll briefs-scroll" style={{ padding: 0 }}>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Niche</th>
            <th>Mood</th>
            <th>Quality</th>
            <th>Revisions</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {briefs.map((b: any) => (
            <tr key={b.id}>
              <td style={{ color: 'var(--text-h)', fontWeight: 500 }}>{fmtDate(b.run_date)}</td>
              <td className="muted" style={{ fontSize: 13 }}>{b.niche_label || 'Default'}</td>
              <td><MoodDot mood={b.signal_mood} /></td>
              <td>
                <span className="num" style={{ fontSize: 13 }}>
                  {b.quality_score != null ? (b.quality_score * 100).toFixed(0) + '%' : '—'}
                </span>
              </td>
              <td className="muted num">{b.revision_count}</td>
              <td><StatusBadge status={b.status} /></td>
              <td>
                <Link to={`/briefs/${b.id}`} className="btn btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }}>
                  View →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
