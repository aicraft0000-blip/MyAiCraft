import { useQuery } from '@tanstack/react-query'
import { listBriefs } from '../api/briefs'
import { listDigests } from '../api/digests'
import BriefsTable from '../components/BriefsTable'
import DigestList from '../components/DigestList'
import { DIGEST_DAYS } from './Dashboard'

// Actioned briefs — posted or archived. They leave the Dashboard the moment
// they're dealt with and live here instead, so the desk only ever shows work.
// Signal sweeps older than the Dashboard's recency window also land here.
const DONE = ['posted', 'archived']

export default function Archive() {
  const { data: briefs, isLoading, error } = useQuery({ queryKey: ['briefs'], queryFn: listBriefs })
  const { data: digests } = useQuery({ queryKey: ['digests'], queryFn: listDigests })
  const done = (briefs || []).filter((b: any) => DONE.includes(b.status))
  const cutoff = Date.now() - DIGEST_DAYS * 86_400_000
  const olderDigests = (digests || []).filter((d: any) => new Date(d.run_date).getTime() < cutoff)

  return (
    <div>
      <div className="page-title">
        Archive
        <p className="page-sub">Briefs you've already actioned, and signal sweeps older than {DIGEST_DAYS} days. Everything is kept; nothing is deleted.</p>
      </div>

      {isLoading && <p className="muted" style={{ fontSize: 13 }}>Loading…</p>}
      {error    && <p className="error-msg">Failed to load briefs.</p>}

      {!isLoading && !error && done.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Nothing archived yet.</p>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 8 }}>
            Once a brief is posted, or you archive it from its page, it moves here.
          </p>
        </div>
      )}

      {done.length > 0 && <BriefsTable briefs={done} />}

      {olderDigests.length > 0 && (
        <div style={{ marginTop: 36 }}>
          <div className="page-title" style={{ fontSize: 16, marginBottom: 12 }}>
            Older daily signals
            <p className="page-sub">Sweeps that have aged off the Dashboard.</p>
          </div>
          <DigestList digests={olderDigests} />
        </div>
      )}
    </div>
  )
}
