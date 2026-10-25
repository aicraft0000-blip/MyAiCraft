import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { suggestSources } from '../api/auth'
import { listNiches, createNiche, updateNiche, deleteNiche, Niche } from '../api/niches'

function Field({ label, hint, value, onChange, type }: { label: string; hint?: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {label}
      </label>
      {hint && <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>{hint}</p>}
      <input type={type || 'text'} value={value} onChange={e => onChange(e.target.value)} />
    </div>
  )
}

function NicheCard({ niche, canDelete }: { niche: Niche; canDelete: boolean }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    label: niche.label || '',
    niche: niche.niche || '',
    avoid_words: niche.avoid_words || '',
    subreddits: niche.subreddits || '',
    github_topics: niche.github_topics || '',
    web_queries: niche.web_queries || '',
    rss_feeds: niche.rss_feeds || '',
    notify_email: niche.notify_email || '',
    active: niche.active,
  })
  const [saved, setSaved] = useState(false)
  const set = (k: keyof typeof form) => (v: string) => setForm(f => ({ ...f, [k]: v }))

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['niches'] })
    qc.invalidateQueries({ queryKey: ['briefs'] })
  }

  const save = useMutation({
    mutationFn: () => updateNiche(niche.id, form),
    onSuccess: () => { invalidate(); setSaved(true); setTimeout(() => setSaved(false), 3000) },
  })
  const del = useMutation({
    mutationFn: () => deleteNiche(niche.id),
    onSuccess: invalidate,
  })

  const [suggesting, setSuggesting] = useState(false)
  const [suggestErr, setSuggestErr] = useState('')
  async function handleSuggest() {
    setSuggestErr('')
    if (!form.niche.trim()) { setSuggestErr('Type this niche first, then let RadarWindow suggest sources.'); return }
    setSuggesting(true)
    try {
      const s = await suggestSources(form.niche)
      setForm(f => ({
        ...f,
        subreddits:    s.subreddits    || f.subreddits,
        github_topics: s.github_topics ?? f.github_topics,
        web_queries:   s.web_queries   || f.web_queries,
      }))
    } catch {
      setSuggestErr('Could not suggest sources just now — try again in a moment.')
    } finally {
      setSuggesting(false)
    }
  }

  const delError = (del.error as any)?.response?.data?.detail as string | undefined

  return (
    <div className="card" style={{ marginBottom: 20, opacity: form.active ? 1 : 0.7 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <input
          value={form.label}
          onChange={e => set('label')(e.target.value)}
          style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-h)', border: 'none', background: 'none', padding: 0, width: 'auto', flex: 1 }}
        />
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
          <input type="checkbox" checked={form.active} onChange={e => setForm(f => ({ ...f, active: e.target.checked }))} style={{ width: 'auto' }} />
          {form.active ? 'Active' : 'Paused'}
        </label>
      </div>

      <Field label="Niche description" hint="One sentence. What world does this niche cover?" value={form.niche} onChange={set('niche')} />
      <Field label="Words to avoid" hint="Comma-separated. These trigger a quality gate failure." value={form.avoid_words} onChange={set('avoid_words')} />

      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
        Not sure where this niche lives? Fill the description above, then let RadarWindow suggest the sources.
      </p>
      <button type="button" onClick={handleSuggest} disabled={suggesting}
        style={{ marginBottom: 16, fontSize: 13, fontWeight: 600, color: 'var(--green)', background: 'none', border: '1px solid var(--green)', borderRadius: 6, padding: '8px 14px', cursor: 'pointer' }}>
        {suggesting ? 'Finding your sources…' : 'Suggest sources for this niche'}
      </button>
      {suggestErr && <p style={{ fontSize: 12, color: 'var(--amber, #d97706)', marginBottom: 12 }}>{suggestErr}</p>}

      <Field label="Subreddits" hint="Comma-separated, no r/ prefix." value={form.subreddits} onChange={set('subreddits')} />
      <Field label="GitHub topics" hint="Comma-separated. e.g. llm,anthropic,mcp" value={form.github_topics} onChange={set('github_topics')} />
      <Field label="Web search queries" hint="Comma-separated. Used by the Anthropic web search tool." value={form.web_queries} onChange={set('web_queries')} />
      <Field label="Your own feeds (RSS)" hint="Comma-separated feed URLs — blogs, newsletters, YouTube channels, news sites. RadarWindow sweeps them alongside the built-in sources." value={form.rss_feeds} onChange={set('rss_feeds')} />
      <Field label="Notify email (optional)" hint="Where this niche's 'draft ready' email goes. Blank = your account default." value={form.notify_email} onChange={set('notify_email')} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 4 }}>
        <button className="btn btn-primary" onClick={() => save.mutate()} disabled={save.isPending}>
          {save.isPending ? 'Saving…' : 'Save niche'}
        </button>
        {saved && <span style={{ fontSize: 13, color: 'var(--green)' }}>✓ Saved</span>}
        {save.error && <span className="error-msg">Save failed. Try again.</span>}
        <span style={{ flex: 1 }} />
        {canDelete && (
          <button className="btn btn-ghost" onClick={() => { if (confirm(`Delete "${form.label}"? Past briefs are kept.`)) del.mutate() }} disabled={del.isPending}
            style={{ fontSize: 12, color: 'var(--amber, #d97706)' }}>
            Delete
          </button>
        )}
      </div>
      {delError && <p className="error-msg" style={{ marginTop: 8 }}>{delError}</p>}
    </div>
  )
}

export default function Niches() {
  const qc = useQueryClient()
  const { data: niches, isLoading } = useQuery({ queryKey: ['niches'], queryFn: listNiches })
  const add = useMutation({
    mutationFn: () => createNiche({ label: 'New niche' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['niches'] }),
  })

  if (isLoading) return <p className="muted" style={{ fontSize: 13 }}>Loading…</p>

  const list = niches || []

  return (
    <div style={{ maxWidth: 600 }}>
      <div className="page-title">
        Niches
        <p className="page-sub">The worlds RadarWindow watches for you. Each niche gets its own weekly brief and daily digest from its own sources — add as many as you want.</p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-h)' }}>
          Your niches {list.length > 0 && <span className="muted">({list.length})</span>}
        </div>
        <button className="btn btn-primary" onClick={() => add.mutate()} disabled={add.isPending} style={{ fontSize: 13 }}>
          {add.isPending ? 'Adding…' : '+ Add niche'}
        </button>
      </div>

      {list.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: 32, marginBottom: 20 }}>
          <p className="muted" style={{ fontSize: 13 }}>No niches yet. Add your first one to start getting briefs.</p>
        </div>
      )}

      {list.map(n => <NicheCard key={n.id} niche={n} canDelete={list.length > 1} />)}
    </div>
  )
}
