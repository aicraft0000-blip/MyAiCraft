import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSettings, updateSettings } from '../api/auth'

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

function AccountCard() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['settings'], queryFn: getSettings })
  const [notify, setNotify] = useState('')
  const [blotato, setBlotato] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => { if (data) setNotify(data.notify_email || '') }, [data])

  const save = useMutation({
    mutationFn: () => {
      const payload: Record<string, string> = {}
      if (notify) payload.notify_email = notify
      if (blotato) payload.blotato_api_key = blotato
      return updateSettings(payload)
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['settings'] }); setSaved(true); setBlotato(''); setTimeout(() => setSaved(false), 3000) },
  })

  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-h)', marginBottom: 16 }}>Account</div>
      <Field label="Default notify email" hint="Used for any niche that doesn't set its own." value={notify} onChange={setNotify} />
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Blotato API key
        </label>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>
          {data?.has_blotato_key ? '✓ Key saved.' : 'No key saved.'} Posting is handled by Blotato — RadarWindow is not responsible for delivery or platform restrictions.
        </p>
        <input type="password" placeholder={data?.has_blotato_key ? 'Leave blank to keep existing key' : 'Paste your Blotato API key'}
          value={blotato} onChange={e => setBlotato(e.target.value)} />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button className="btn btn-primary" onClick={() => save.mutate()} disabled={save.isPending}>
          {save.isPending ? 'Saving…' : 'Save account'}
        </button>
        {saved && <span style={{ fontSize: 13, color: 'var(--green)' }}>✓ Saved</span>}
      </div>
    </div>
  )
}

export default function Settings() {
  return (
    <div style={{ maxWidth: 600 }}>
      <div className="page-title">
        Settings
        <p className="page-sub">Account-level settings. Your niches and their sources live in <Link to="/niches" style={{ color: 'var(--green)', fontWeight: 600 }}>Niches</Link>.</p>
      </div>
      <AccountCard />
    </div>
  )
}
