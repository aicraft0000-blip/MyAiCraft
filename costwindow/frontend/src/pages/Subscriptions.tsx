import { useState } from 'react'
import { useSubscriptions } from '../hooks/useSubscriptions'
import KillSwitch from '../components/ui/KillSwitch'

function nextRenewalLabel(renewal_day: number | null): string {
  if (renewal_day === null) return '—'
  const today = new Date()
  let year = today.getFullYear()
  let month = today.getMonth()
  const candidate = new Date(year, month, Math.min(renewal_day, 28))
  if (candidate <= today) {
    month += 1
    if (month > 11) { month = 0; year += 1 }
  }
  const d = new Date(year, month, Math.min(renewal_day, 28))
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function Subscriptions() {
  const { data, isLoading, add, toggle, remove, update } = useSubscriptions()
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ name: '', cost_gbp: '', renewal_day: '', cancel_url: '' })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState({ name: '', cost_gbp: '', renewal_day: '', cancel_url: '' })

  const startEdit = (sub: any) => {
    setEditingId(sub.id)
    setEditForm({
      name: sub.name,
      cost_gbp: String(sub.cost_gbp),
      renewal_day: sub.renewal_day ? String(sub.renewal_day) : '',
      cancel_url: sub.cancel_url || '',
    })
  }

  const saveEdit = async () => {
    if (!editingId || !editForm.name || !editForm.cost_gbp) return
    setSaving(true)
    try {
      await update(editingId, {
        name: editForm.name,
        cost_gbp: parseFloat(editForm.cost_gbp),
        renewal_day: editForm.renewal_day ? parseInt(editForm.renewal_day) : undefined,
        cancel_url: editForm.cancel_url || undefined,
      })
      setEditingId(null)
    } finally {
      setSaving(false)
    }
  }

  const handleAdd = async () => {
    if (!form.name || !form.cost_gbp) return
    setSaving(true)
    setFormError('')
    try {
      await add({
        name: form.name,
        cost_gbp: parseFloat(form.cost_gbp),
        renewal_day: form.renewal_day ? parseInt(form.renewal_day) : undefined,
        cancel_url: form.cancel_url || undefined,
      })
      setForm({ name: '', cost_gbp: '', renewal_day: '', cancel_url: '' })
      setShowAdd(false)
    } catch (e: any) {
      setFormError(e?.response?.data?.detail || 'Failed to save. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const totalMonthly = data.filter(s => s.is_active).reduce((sum, s) => sum + s.cost_gbp, 0)

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Subscriptions</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            Monthly total: <span className="num" style={{ color: 'var(--amber)' }}>£{totalMonthly.toFixed(2)}</span>
          </span>
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Add Subscription</button>
        </div>
      </div>

      {showAdd && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 2fr auto', gap: 8 }}>
            <input className="input" placeholder="Service name (e.g. Blotato)" value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            <input className="input" placeholder="£/month" type="number" step="0.01" value={form.cost_gbp}
              onChange={e => setForm(f => ({ ...f, cost_gbp: e.target.value }))} />
            <input className="input" placeholder="Renewal day (1-31)" type="number" min="1" max="31" value={form.renewal_day}
              onChange={e => setForm(f => ({ ...f, renewal_day: e.target.value }))} />
            <input className="input" placeholder="Cancel URL (optional)" value={form.cancel_url}
              onChange={e => setForm(f => ({ ...f, cancel_url: e.target.value }))} />
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary" onClick={handleAdd} disabled={saving}>
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button className="btn btn-ghost" onClick={() => { setShowAdd(false); setFormError('') }}>Cancel</button>
            </div>
          </div>
          {formError && (
            <p style={{ color: 'var(--red)', fontSize: 12, marginTop: 8 }}>{formError}</p>
          )}
        </div>
      )}

      {isLoading ? (
        <div style={{ color: 'var(--text-muted)', padding: 40 }}>Loading...</div>
      ) : (
        <div className="card card-table">
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-muted)', fontSize: 11, fontWeight: 500 }}>SERVICE</th>
                <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)', fontSize: 11, fontWeight: 500 }}>MONTHLY</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-muted)', fontSize: 11, fontWeight: 500 }}>NEXT RENEWAL</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-muted)', fontSize: 11, fontWeight: 500 }}>STATUS</th>
                <th style={{ textAlign: 'center', padding: '8px 12px', color: 'var(--text-muted)', fontSize: 11, fontWeight: 500 }}>KILL</th>
                <th style={{ padding: '8px 12px' }}></th>
              </tr>
            </thead>
            <tbody>
              {data.map(sub => (
                editingId === sub.id ? (
                  <tr key={sub.id} style={{ borderBottom: '1px solid var(--border)', background: 'rgba(245,158,11,0.05)' }}>
                    <td style={{ padding: '8px 12px' }}>
                      <input className="input" value={editForm.name} style={{ width: '100%' }}
                        onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))} />
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <input className="input" type="number" step="0.01" value={editForm.cost_gbp} style={{ width: 90 }}
                        onChange={e => setEditForm(f => ({ ...f, cost_gbp: e.target.value }))} />
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <input className="input" type="number" min="1" max="31" placeholder="day" value={editForm.renewal_day} style={{ width: 70 }}
                        onChange={e => setEditForm(f => ({ ...f, renewal_day: e.target.value }))} />
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <input className="input" placeholder="Cancel URL" value={editForm.cancel_url} style={{ width: '100%' }}
                        onChange={e => setEditForm(f => ({ ...f, cancel_url: e.target.value }))} />
                    </td>
                    <td colSpan={2} style={{ padding: '8px 12px', textAlign: 'right' }}>
                      <button className="btn btn-primary" style={{ fontSize: 11, marginRight: 6 }} onClick={saveEdit} disabled={saving}>
                        {saving ? 'Saving…' : 'Save'}
                      </button>
                      <button className="btn btn-ghost" style={{ fontSize: 11 }} onClick={() => setEditingId(null)}>Cancel</button>
                    </td>
                  </tr>
                ) : (
                <tr key={sub.id} style={{
                  borderBottom: '1px solid var(--border)',
                  background: !sub.is_active ? 'rgba(220,53,69,0.05)' : undefined
                }}>
                  <td style={{ padding: '10px 12px', fontSize: 13 }}>{sub.name}</td>
                  <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                    <span className="num">£{sub.cost_gbp.toFixed(2)}/mo</span>
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: 12 }}>
                    {nextRenewalLabel(sub.renewal_day)}
                  </td>
                  <td style={{ padding: '10px 12px', fontSize: 12 }}>
                    {sub.is_active ? (
                      <span style={{ color: 'var(--green)' }}>● Active</span>
                    ) : (
                      <div>
                        <span style={{ color: 'var(--red)' }}>⚠ Flagged</span>
                        {sub.cancel_url && (
                          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                            Cancel at: <a href={sub.cancel_url} target="_blank" rel="noreferrer"
                              style={{ color: 'var(--amber)' }}>{sub.cancel_url}</a>
                          </div>
                        )}
                      </div>
                    )}
                  </td>
                  <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                    <KillSwitch
                      processId={sub.id}
                      label={sub.name}
                      isActive={sub.is_active}
                      onToggle={toggle}
                    />
                  </td>
                  <td style={{ padding: '10px 12px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <button className="btn btn-ghost" style={{ fontSize: 11 }}
                      onClick={() => startEdit(sub)}>
                      Edit
                    </button>
                    <button className="btn btn-ghost" style={{ fontSize: 11, color: 'var(--text-muted)' }}
                      onClick={() => { if (confirm(`Remove ${sub.name}?`)) remove(sub.id) }}>
                      Remove
                    </button>
                  </td>
                </tr>
                )
              ))}
              {data.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                    No subscriptions yet. Add your first one above.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
