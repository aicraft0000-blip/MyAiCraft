import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getBrief, patchBrief, approveBrief, patchPost, downloadMediaKit } from '../api/briefs'
import Markdown from '../components/Markdown'

const PLATFORMS = ['x', 'linkedin', 'instagram'] as const
const PLATFORM_LABELS: Record<string, string> = { x: 'X / Twitter', linkedin: 'LinkedIn', instagram: 'Instagram' }

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function BriefDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [activeTab,    setActiveTab]    = useState<string>('brief')
  const [editingBrief, setEditingBrief] = useState(false)
  const [briefDraft,   setBriefDraft]   = useState('')
  const [editingPost,  setEditingPost]  = useState<string | null>(null)
  const [postDraft,    setPostDraft]    = useState('')
  const [downloading,  setDownloading]  = useState(false)

  async function handleDownload() {
    setDownloading(true)
    try { await downloadMediaKit(id!) } catch { /* surfaced via button state */ }
    finally { setDownloading(false) }
  }

  const { data, isLoading, error } = useQuery({
    queryKey: ['brief', id],
    queryFn: () => getBrief(id!),
  })

  const saveBrief = useMutation({
    mutationFn: (content_md: string) => patchBrief(id!, { content_md }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['brief', id] }); setEditingBrief(false) },
  })

  const approve = useMutation({
    mutationFn: () => approveBrief(id!),
    onSuccess: (res: any) => {
      qc.invalidateQueries({ queryKey: ['brief', id] })
      qc.invalidateQueries({ queryKey: ['briefs'] })
      window.alert(res?.message || 'Approved and posted.')
    },
    onError: (err: any) => {
      window.alert(err?.response?.data?.detail || 'Something went wrong while posting. Your brief is saved as approved and the Monday run will retry.')
    },
  })

  const confirmAndApprove = () => {
    const ok = window.confirm(
      'Approve & post this brief now?\n\n' +
      'It will go out to your connected platforms (X, LinkedIn, Instagram) within a few minutes, staggered.\n\n' +
      'Posts can only be cancelled from your Blotato dashboard afterwards — there is no undo here.'
    )
    if (ok) approve.mutate()
  }

  const archive = useMutation({
    mutationFn: () => patchBrief(id!, { status: 'archived' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['briefs'] }); navigate('/dashboard') },
  })

  const savePost = useMutation({
    mutationFn: ({ postId, content }: { postId: string; content: string }) => patchPost(postId, { content }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['brief', id] }); setEditingPost(null) },
  })

  const togglePublic = useMutation({
    mutationFn: (is_public: boolean) => patchBrief(id!, { is_public }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['brief', id] }),
  })

  if (isLoading) return <p className="muted" style={{ fontSize: 13, padding: 28 }}>Loading…</p>
  if (error || !data) return <p className="error-msg" style={{ padding: 28 }}>Failed to load brief.</p>

  const brief = data
  const posts: any[] = brief.posts || []
  const audit: any[] = brief.audit_log || []
  const isDraft = brief.status === 'draft'

  const postFor = (platform: string) => posts.find((p: any) => p.platform === platform)

  return (
    <div style={{ maxWidth: 760 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <button className="btn btn-ghost" style={{ fontSize: 12, padding: '4px 8px', marginBottom: 10 }}
            onClick={() => navigate('/dashboard')}>← Back</button>
          <div className="page-title" style={{ marginBottom: 4 }}>
            Brief — {fmtDate(brief.run_date)}
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', fontSize: 12, color: 'var(--text-muted)' }}>
            <span className={`badge badge-${brief.status}`}>{brief.status}</span>
            {brief.quality_score != null && (
              <span>Quality <span className="num">{(brief.quality_score * 100).toFixed(0)}%</span></span>
            )}
            <span>{brief.revision_count} revision{brief.revision_count !== 1 ? 's' : ''}</span>
            {brief.niche_voice_passed && <span style={{ color: 'var(--green)' }}>✓ Niche voice</span>}
          </div>
          {brief.source_health && (
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 10, fontSize: 11, color: 'var(--text-muted)', flexWrap: 'wrap' }}>
              <span style={{ textTransform: 'uppercase', letterSpacing: '0.06em' }}>Sources:</span>
              {Object.entries(brief.source_health as Record<string, number>).map(([src, n]) => (
                <span key={src} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: n > 0 ? 'var(--green)' : 'var(--text-muted)', opacity: n > 0 ? 1 : 0.4 }} />
                  {src} <span className="num">{n}</span>
                </span>
              ))}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {brief.is_public && brief.public_slug ? (
            <>
              <a className="btn btn-ghost" style={{ fontSize: 12, color: 'var(--green)' }}
                href={`/p/${brief.public_slug}`} target="_blank" rel="noreferrer" title="Open the public brief page">
                Public ✓ (view)
              </a>
              <button className="btn btn-ghost" style={{ fontSize: 12 }}
                onClick={() => togglePublic.mutate(false)} disabled={togglePublic.isPending}>
                Unpublish
              </button>
            </>
          ) : (
            <button className="btn btn-ghost" style={{ fontSize: 12 }}
              onClick={() => togglePublic.mutate(true)} disabled={togglePublic.isPending}
              title="Publish this brief on the public archive at /p">
              {togglePublic.isPending ? 'Publishing…' : 'Make public'}
            </button>
          )}
          <button className="btn btn-primary" style={{ fontSize: 12 }}
            onClick={handleDownload} disabled={downloading} title="Download the full media kit (brief, posts, signals, media)">
            {downloading ? 'Preparing…' : '↓ Download kit'}
          </button>
          {isDraft && (
            <>
              <button className="btn btn-danger" style={{ fontSize: 12 }}
                onClick={() => archive.mutate()} disabled={archive.isPending}>
                Archive
              </button>
              <button className="btn btn-primary" style={{ fontSize: 12 }}
                onClick={confirmAndApprove} disabled={approve.isPending}
                title="Approve this brief and post it to your connected platforms now">
                {approve.isPending ? 'Posting…' : 'Approve & post'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button className={`tab${activeTab === 'brief' ? ' active' : ''}`} onClick={() => setActiveTab('brief')}>Intelligence brief</button>
        {PLATFORMS.map(p => (
          <button key={p} className={`tab${activeTab === p ? ' active' : ''}`} onClick={() => setActiveTab(p)}>
            {PLATFORM_LABELS[p]}
          </button>
        ))}
        {audit.length > 0 && (
          <button className={`tab${activeTab === 'audit' ? ' active' : ''}`} onClick={() => setActiveTab('audit')}>Audit log</button>
        )}
      </div>

      {/* Brief tab */}
      {activeTab === 'brief' && (
        <div className="card">
          {!editingBrief ? (
            <>
              <Markdown md={brief.content_md} />
              {isDraft && (
                <button className="btn btn-ghost" style={{ marginTop: 20, fontSize: 12 }}
                  onClick={() => { setBriefDraft(brief.content_md); setEditingBrief(true) }}>
                  Edit brief
                </button>
              )}
            </>
          ) : (
            <>
              <textarea
                value={briefDraft}
                onChange={e => setBriefDraft(e.target.value)}
                style={{ minHeight: 400, fontFamily: 'var(--mono)', fontSize: 13 }}
              />
              <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                <button className="btn btn-primary" style={{ fontSize: 12 }}
                  onClick={() => saveBrief.mutate(briefDraft)} disabled={saveBrief.isPending}>
                  {saveBrief.isPending ? 'Saving…' : 'Save'}
                </button>
                <button className="btn btn-ghost" style={{ fontSize: 12 }}
                  onClick={() => setEditingBrief(false)}>Cancel</button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Platform post tabs */}
      {PLATFORMS.includes(activeTab as any) && (() => {
        const post = postFor(activeTab)
        if (!post) return <div className="card"><p className="muted">No post generated for this platform.</p></div>
        return (
          <div className="card">
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              {PLATFORM_LABELS[activeTab]} — {post.status}
            </div>
            {editingPost !== post.id ? (
              <>
                <p style={{ fontSize: 14, lineHeight: 1.65, whiteSpace: 'pre-wrap', color: 'var(--text-h)' }}>{post.content}</p>
                {post.image_public_url && (
                  <img src={post.image_public_url} alt="Generated" style={{ marginTop: 16, maxWidth: '100%', borderRadius: 8 }} />
                )}
                {isDraft && (
                  <button className="btn btn-ghost" style={{ marginTop: 16, fontSize: 12 }}
                    onClick={() => { setPostDraft(post.content); setEditingPost(post.id) }}>
                    Edit
                  </button>
                )}
              </>
            ) : (
              <>
                <textarea
                  value={postDraft}
                  onChange={e => setPostDraft(e.target.value)}
                  style={{ minHeight: 200, fontSize: 14 }}
                />
                <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                  <button className="btn btn-primary" style={{ fontSize: 12 }}
                    onClick={() => savePost.mutate({ postId: post.id, content: postDraft })}
                    disabled={savePost.isPending}>
                    {savePost.isPending ? 'Saving…' : 'Save'}
                  </button>
                  <button className="btn btn-ghost" style={{ fontSize: 12 }}
                    onClick={() => setEditingPost(null)}>Cancel</button>
                </div>
              </>
            )}
          </div>
        )
      })()}

      {/* Audit log tab */}
      {activeTab === 'audit' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table>
            <thead><tr><th>Time</th><th>Platform</th><th>Action</th><th>Scheduled for</th></tr></thead>
            <tbody>
              {audit.map((entry: any) => (
                <tr key={entry.id}>
                  <td className="muted num">{fmtDate(entry.created_at)}</td>
                  <td style={{ textTransform: 'capitalize' }}>{entry.platform}</td>
                  <td><span style={{ color: entry.action === 'failed' ? 'var(--red)' : 'var(--green)' }}>{entry.action}</span></td>
                  <td className="muted num">{entry.scheduled_for ? fmtDate(entry.scheduled_for) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
