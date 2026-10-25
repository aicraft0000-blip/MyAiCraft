import { useState } from 'react'
import Markdown from './Markdown'

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function DigestList({ digests }: { digests: any[] }) {
  const [open, setOpen] = useState<string | null>(null)

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {digests.map((d: any) => (
        <div key={d.id} style={{ borderBottom: '1px solid var(--border)' }}>
          <button
            onClick={() => setOpen(open === d.id ? null : d.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 16, width: '100%', padding: '10px 16px',
              background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left', font: 'inherit', fontSize: 13,
            }}>
            <span className="num" style={{ color: 'var(--text-h)', fontWeight: 500, whiteSpace: 'nowrap' }}>{fmtDate(d.run_date)}</span>
            <span className="muted" style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {d.signals?.[0]?.title || '—'}
            </span>
            <span className="muted">{open === d.id ? '−' : '+'}</span>
          </button>
          {open === d.id && (
            <div style={{ padding: '0 16px 16px' }}>
              {d.signals?.length ? (
                <>
                  <ol style={{ margin: '10px 0 0', paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {d.signals.map((s: any, i: number) => (
                      <li key={i} style={{ fontSize: 13, lineHeight: 1.5 }}>
                        <a href={s.url} target="_blank" rel="noopener" style={{ color: 'var(--text-h)', fontWeight: 600 }}>{s.title}</a>
                        <span className="muted"> — {s.source} · score {Number(s.combined_score).toFixed(2)}</span>
                        {s.make_brief_url && (
                          <a href={s.make_brief_url} target="_blank" rel="noopener"
                            style={{ marginLeft: 10, fontSize: 12, color: 'var(--green)', fontWeight: 600, whiteSpace: 'nowrap' }}>
                            Make this a brief →
                          </a>
                        )}
                      </li>
                    ))}
                  </ol>
                  {d.source_health && (
                    <p className="muted" style={{ fontSize: 12, marginTop: 12 }}>
                      Sources: {Object.entries(d.source_health).map(([k, v]) => `${k} ${v}`).join(' · ')}
                    </p>
                  )}
                </>
              ) : (
                <Markdown md={d.content_md} />
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
