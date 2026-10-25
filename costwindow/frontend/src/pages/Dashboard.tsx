import React, { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useSummary } from '../hooks/useSummary'
import { useProcesses, useToggleProcess } from '../hooks/useProcesses'
import { useSubscriptions } from '../hooks/useSubscriptions'
import { useProviderBalances } from '../hooks/useProviderBalances'
import { updateProcessBudget } from '../api/processes'
import { recordManualBalance } from '../api/providerBalances'
import { useCurrency } from '../contexts/CurrencyContext'
import KillSwitch from '../components/ui/KillSwitch'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function nextRenewalLabel(renewal_day: number | null): string {
  if (renewal_day === null || renewal_day === undefined) return '—'
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

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`
  return String(n)
}

function groupByProvider(processes: any[]): Record<string, any[]> {
  const out: Record<string, any[]> = {}
  for (const p of processes) {
    const key = p.provider || 'other'
    if (!out[key]) out[key] = []
    out[key].push(p)
  }
  return out
}

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Anthropic API Key',
  openai:    'OpenAI API Key',
  google:    'Google AI API Key',
  other:     'Other',
}

function PriceTag({ p, format }: { p: any; format: (usd: number) => string }) {
  const open = p.cost_driver === 'demand'
  if (!p.runs_per_week) {
    return <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>no recent runs</span>
  }
  return (
    <span style={{ fontSize: 12 }}>
      <span className="num">{format(p.cost_per_run_usd ?? 0)}</span>
      <span style={{ color: 'var(--text-muted)' }}>/run · {p.runs_per_week}×wk ≈ </span>
      <span className="num">{format(p.projected_month_usd ?? 0)}</span>
      <span style={{ color: 'var(--text-muted)' }}>/mo </span>
      <span style={{
        fontSize: 9, fontWeight: 700, letterSpacing: '0.05em', marginLeft: 4,
        color: open ? 'var(--red)' : 'var(--green)',
        background: open ? 'rgba(220,53,69,0.12)' : 'rgba(16,185,129,0.12)',
        padding: '2px 5px', borderRadius: 4,
      }}>{open ? 'OPEN-ENDED' : 'CAPPED'}</span>
    </span>
  )
}

function BudgetCell({ p, format, onSaved }: { p: any; format: (usd: number) => string; onSaved: () => void }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState<string>(p.budget_usd_month ? String(p.budget_usd_month) : '')
  const [action, setAction] = useState<'warn' | 'block'>(p.budget_action === 'block' ? 'block' : 'warn')

  async function save() {
    await updateProcessBudget(p.id, {
      budget_usd_month: value === '' ? 0 : parseFloat(value),
      budget_action: action,
    })
    setEditing(false)
    onSaved()
  }

  if (editing) {
    return (
      <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
        <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>$</span>
        <input value={value} onChange={e => setValue(e.target.value)} placeholder="none"
          style={{ width: 52, fontSize: 12, padding: '2px 4px', background: 'var(--surface)',
            color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 4 }} />
        <select value={action} onChange={e => setAction(e.target.value as 'warn' | 'block')}
          style={{ fontSize: 11, padding: '2px 2px', background: 'var(--surface)',
            color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 4 }}>
          <option value="warn">warn</option>
          <option value="block">block</option>
        </select>
        <button className="btn btn-ghost" style={{ fontSize: 11 }} onClick={save}>✓</button>
        <button className="btn btn-ghost" style={{ fontSize: 11 }} onClick={() => setEditing(false)}>✕</button>
      </span>
    )
  }

  const state = p.budget?.state
  const colour = state === 'exceeded' ? 'var(--red)' : state === 'warning' ? 'var(--amber)' : 'var(--text-muted)'
  return (
    <button className="btn btn-ghost" style={{ fontSize: 12, padding: '2px 6px' }} onClick={() => setEditing(true)}>
      {p.budget_usd_month ? (
        <span style={{ color: colour }}>
          {format(p.budget_usd_month)}/mo
          {p.budget?.used_pct != null && <> · {p.budget.used_pct}%</>}
          {p.budget_action === 'block' && <> 🔒</>}
        </span>
      ) : (
        <span style={{ color: 'var(--text-muted)' }}>set budget →</span>
      )}
    </button>
  )
}

export default function Dashboard() {
  const qc = useQueryClient()
  const { data: summary, isLoading: summaryLoading } = useSummary()
  const { data: processes, isLoading: processesLoading } = useProcesses()
  const { data: subscriptions, toggle: toggleSub } = useSubscriptions()
  const { data: balanceData } = useProviderBalances()
  const { mutateAsync: toggleProcess } = useToggleProcess()
  const { format } = useCurrency()
  const [balanceEdit, setBalanceEdit] = useState<{ provider: string; value: string } | null>(null)

  // Track which process is being linked to a subscription
  const [linking, setLinking] = useState<string | null>(null)

  const retry = () => {
    qc.invalidateQueries({ queryKey: ['summary'] })
    qc.invalidateQueries({ queryKey: ['processes'] })
    qc.invalidateQueries({ queryKey: ['subscriptions'] })
  }

  if (summaryLoading || processesLoading) {
    return <div style={{ color: 'var(--text-muted)', padding: 40 }}>Loading…</div>
  }
  if (!summary) {
    return (
      <div style={{ color: 'var(--red)', padding: 40, display: 'flex', alignItems: 'center', gap: 12 }}>
        Failed to load data.
        <button className="btn btn-ghost" style={{ fontSize: 12 }} onClick={retry}>↻ Retry</button>
      </div>
    )
  }

  const allProcesses: any[] = processes || []

  // Subscription-type processes (covered by a flat plan — no £ billing)
  const subProcesses = allProcesses.filter((p: any) => p.billing_type === 'subscription')
  // API-type processes (real per-token cost)
  const apiProcesses = allProcesses.filter((p: any) => p.billing_type !== 'subscription')
  const apiByProvider = groupByProvider(apiProcesses)

  const apiTotalToday = apiProcesses.reduce((s: number, p: any) => s + (p.today_cost_usd || 0), 0)
  const apiTotalMonth = apiProcesses.reduce((s: number, p: any) => s + (p.this_month_cost_usd || 0), 0)

  async function linkProcess(processId: string, subscriptionId: string | null) {
    await api.patch(`/processes/${processId}/link`, { subscription_id: subscriptionId })
    qc.invalidateQueries({ queryKey: ['processes'] })
    setLinking(null)
  }

  function ProcessSubRow({ p }: { p: any }) {
    return (
      <tr key={p.id} style={{ background: 'rgba(255,255,255,0.02)' }}>
        <td style={{ padding: '8px 12px 8px 32px', fontSize: 12, color: 'var(--text-muted)' }}>
          └ {p.label}
        </td>
        <td style={{ padding: '8px 12px', fontSize: 12 }}>
          <span style={{ color: 'var(--amber)', fontFamily: 'var(--font-num)' }}>
            {formatTokens(p.tokens_today || 0)}
          </span>
          <span style={{ color: 'var(--text-muted)', marginLeft: 4 }}>tokens today</span>
        </td>
        <td style={{ padding: '8px 12px', fontSize: 12, color: 'var(--text-muted)' }}>
          {formatTokens(p.tokens_month || 0)} this month
        </td>
        <td style={{ padding: '8px 12px', fontSize: 12, color: 'var(--text-muted)' }}>
          {formatDateTime(p.last_called_at)}
        </td>
        <td style={{ padding: '8px 12px' }}>
          <span style={{
            fontSize: 10, fontWeight: 600, letterSpacing: '0.05em',
            color: 'var(--green)', background: 'rgba(16,185,129,0.12)',
            padding: '2px 6px', borderRadius: 4,
          }}>INCLUDED</span>
        </td>
        <td style={{ padding: '8px 12px', textAlign: 'center' }}>
          <KillSwitch processId={p.id} label={p.label} isActive={p.is_active}
            onToggle={(id, active) => toggleProcess({ id, isActive: active })} />
        </td>
      </tr>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>

      {/* ── SUBSCRIPTIONS ─────────────────────────────────── */}
      <section>
        <h2 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 12,
          textTransform: 'uppercase', letterSpacing: '0.08em', display: 'flex', alignItems: 'center', gap: 10 }}>
          Subscriptions
          {summary.subscriptions_monthly_gbp > 0 && (
            <span style={{ color: 'var(--amber)', fontFamily: 'var(--font-num)', fontWeight: 400 }}>
              £{(summary.subscriptions_monthly_gbp || 0).toFixed(2)}/mo
            </span>
          )}
        </h2>
        <div className="card card-table">
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['SERVICE / TOOL', 'USAGE', 'PERIOD', 'LAST ACTIVE', 'COST / STATUS', 'KILL'].map(h => (
                  <th key={h} style={{ textAlign: h === 'KILL' ? 'center' : 'left',
                    padding: '8px 12px', color: 'var(--text-muted)', fontSize: 11, fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(subscriptions || []).length === 0 ? (
                <tr><td colSpan={6} style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                  No subscriptions yet. <Link to="/subscriptions" style={{ color: 'var(--amber)' }}>Add one</Link>
                </td></tr>
              ) : (subscriptions || []).map((sub: any) => {
                const children = subProcesses.filter((p: any) => p.subscription_id === sub.id)
                return (
                  <React.Fragment key={sub.id}>
                    {/* Subscription parent row */}
                    <tr style={{
                      borderBottom: children.length > 0 ? '1px solid rgba(255,255,255,0.04)' : '1px solid var(--border)',
                      background: !sub.is_active ? 'rgba(220,53,69,0.04)' : undefined,
                    }}>
                      <td style={{ padding: '10px 12px', fontSize: 13, fontWeight: 500 }}>{sub.name}</td>
                      <td style={{ padding: '10px 12px', fontSize: 12, color: 'var(--text-muted)' }}>—</td>
                      <td style={{ padding: '10px 12px', fontSize: 12, color: 'var(--text-muted)' }}>—</td>
                      <td style={{ padding: '10px 12px', fontSize: 12, color: 'var(--text-muted)' }}>—</td>
                      <td style={{ padding: '10px 12px' }}>
                        <span className="num">£{sub.cost_gbp.toFixed(2)}/mo</span>
                        {sub.renewal_day && (
                          <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 8 }}>
                            · renews {nextRenewalLabel(sub.renewal_day)}
                          </span>
                        )}
                        {!sub.is_active && (
                          <span style={{ color: 'var(--red)', fontSize: 11, marginLeft: 8 }}>⚠ flagged</span>
                        )}
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                        <KillSwitch processId={sub.id} label={sub.name} isActive={sub.is_active}
                          onToggle={(id, active) => toggleSub(id, active)} />
                      </td>
                    </tr>

                    {/* Child tools that use this subscription */}
                    {children.map((p: any) => <ProcessSubRow key={p.id} p={p} />)}

                    {/* No children hint */}
                    {children.length === 0 && (
                      <tr style={{ borderBottom: '1px solid var(--border)' }}>
                        <td colSpan={6} style={{ padding: '6px 12px 8px 32px', fontSize: 11, color: 'var(--text-muted)' }}>
                          └ No tools linked yet — link a process below ↓
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Unlinked subscription-type processes */}
        {subProcesses.filter((p: any) => !p.subscription_id).length > 0 && (
          <div className="card" style={{ marginTop: 8, borderColor: 'var(--amber)', opacity: 0.85 }}>
            <div style={{ padding: '10px 12px', fontSize: 12, color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}>
              Subscription tools not yet linked to a plan:
            </div>
            {subProcesses.filter((p: any) => !p.subscription_id).map((p: any) => (
              <div key={p.id} style={{ padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 12,
                borderBottom: '1px solid var(--border)' }}>
                <span style={{ fontSize: 13, flex: 1 }}>{p.label}</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {formatTokens(p.tokens_month || 0)} tokens this month
                </span>
                {linking === p.id ? (
                  <div style={{ display: 'flex', gap: 6 }}>
                    <select
                      style={{ fontSize: 12, padding: '2px 6px', background: 'var(--surface)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 4 }}
                      onChange={e => e.target.value && linkProcess(p.id, e.target.value)}
                      defaultValue=""
                    >
                      <option value="" disabled>Pick subscription…</option>
                      {(subscriptions || []).map((s: any) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                    <button className="btn btn-ghost" style={{ fontSize: 11 }} onClick={() => setLinking(null)}>✕</button>
                  </div>
                ) : (
                  <button className="btn btn-ghost" style={{ fontSize: 11 }}
                    onClick={() => setLinking(p.id)}>
                    Link to subscription →
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── API BILLING ────────────────────────────────────── */}
      <section>
        <h2 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 12,
          textTransform: 'uppercase', letterSpacing: '0.08em', display: 'flex', alignItems: 'center', gap: 10 }}>
          API Billing
          {apiTotalToday > 0 && (
            <span style={{ color: 'var(--red)', fontFamily: 'var(--font-num)', fontWeight: 400 }}>
              {format(apiTotalToday)} today
            </span>
          )}
          {apiTotalMonth > 0 && (
            <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-num)', fontWeight: 400, fontSize: 12 }}>
              · {format(apiTotalMonth)}/mo
            </span>
          )}
        </h2>

        {Object.keys(apiByProvider).length === 0 ? (
          <div className="card" style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            No API processes yet.
          </div>
        ) : Object.entries(apiByProvider).map(([provider, procs]) => (
          <div key={provider} style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.06em',
              textTransform: 'uppercase', marginBottom: 6, paddingLeft: 4 }}>
              {PROVIDER_LABELS[provider] || provider}
            </div>
            <div className="card card-table">
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['PROCESS', 'PRICE TAG', 'THIS MONTH', 'BUDGET', 'STATUS', 'KILL'].map(h => (
                      <th key={h} style={{ textAlign: h === 'KILL' ? 'center' : 'left',
                        padding: '8px 12px', color: 'var(--text-muted)', fontSize: 11, fontWeight: 500 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(procs as any[]).map((p: any) => (
                    <tr key={p.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '10px 12px', fontSize: 13 }}>
                        {p.label}
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          last call {formatDateTime(p.last_called_at)}
                        </div>
                      </td>
                      <td style={{ padding: '10px 12px' }}><PriceTag p={p} format={format} /></td>
                      <td style={{ padding: '10px 12px' }}>
                        <span className="num">{format(p.this_month_cost_usd ?? 0)}</span>
                        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}> · {format(p.today_cost_usd ?? 0)} today</span>
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <BudgetCell p={p} format={format} onSaved={() => qc.invalidateQueries({ queryKey: ['processes'] })} />
                      </td>
                      <td style={{ padding: '10px 12px', fontSize: 12 }}>
                        {p.is_active
                          ? <span style={{ color: 'var(--green)' }}>● Live</span>
                          : p.blocked_reason === 'budget_exceeded'
                            ? <span style={{ color: 'var(--red)' }}>● Budget hit — blocked until 1st</span>
                            : <span style={{ color: 'var(--red)' }}>● Disabled</span>}
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                        <KillSwitch processId={p.id} label={p.label} isActive={p.is_active}
                          onToggle={(id, active) => toggleProcess({ id, isActive: active })} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </section>

      {/* ── PROVIDER BALANCES ──────────────────────────────── */}
      <section>
        <h2 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 12,
          textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          Provider Balances
        </h2>
        <div className="card card-table">
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['PROVIDER', 'BALANCE NOW (EST.)', 'RUNWAY', 'TRACKING GAP', ''].map((h, i) => (
                  <th key={i} style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-muted)', fontSize: 11, fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                { provider: 'anthropic', name: 'Anthropic', console: 'https://console.anthropic.com/settings/billing' },
                { provider: 'openai', name: 'OpenAI', console: 'https://platform.openai.com/settings/organization/billing/overview' },
              ].map(({ provider, name, console: consoleUrl }) => {
                const b = (balanceData?.balances || []).find((x: any) => x.provider === provider)
                const editing = balanceEdit?.provider === provider
                return (
                  <tr key={provider} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '10px 12px', fontSize: 13 }}>
                      {name}
                      <div>
                        <a href={consoleUrl} target="_blank" rel="noreferrer"
                          style={{ color: 'var(--amber)', fontSize: 11 }}>console →</a>
                      </div>
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 12 }}>
                      {b?.estimated_balance_usd != null ? (
                        <>
                          <span className="num" style={{ color: b.estimated_balance_usd <= 0 ? 'var(--red)' : undefined }}>
                            {format(b.estimated_balance_usd)}
                          </span>
                          <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                            {' '}· entered {formatDateTime(b.fetched_at)}
                          </span>
                        </>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>not recorded yet</span>
                      )}
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 12 }}>
                      {b?.runway_days != null ? (
                        <span style={{ color: b.runway_days <= 7 ? 'var(--red)' : b.runway_days <= 14 ? 'var(--amber)' : 'var(--green)' }}>
                          {b.runway_days >= 999 ? '∞' : `~${Math.round(b.runway_days)} days`}
                        </span>
                      ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 12 }}>
                      {b?.reconciliation?.alert ? (
                        <span style={{ color: 'var(--red)' }}>
                          ⚠ {format(b.reconciliation.untracked_spend_usd ?? 0)} untracked
                        </span>
                      ) : b?.reconciliation ? (
                        <span style={{ color: 'var(--green)' }}>✓ all spend tracked</span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>needs 2+ balance entries</span>
                      )}
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 12, textAlign: 'right' }}>
                      {editing ? (
                        <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
                          <span style={{ color: 'var(--text-muted)' }}>$</span>
                          <input autoFocus value={balanceEdit.value}
                            onChange={e => setBalanceEdit({ provider, value: e.target.value })}
                            style={{ width: 64, fontSize: 12, padding: '2px 4px', background: 'var(--surface)',
                              color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 4 }} />
                          <button className="btn btn-ghost" style={{ fontSize: 11 }}
                            onClick={async () => {
                              const v = parseFloat(balanceEdit.value)
                              if (!isNaN(v) && v >= 0) {
                                await recordManualBalance(provider, v)
                                qc.invalidateQueries({ queryKey: ['provider-balances'] })
                              }
                              setBalanceEdit(null)
                            }}>✓</button>
                          <button className="btn btn-ghost" style={{ fontSize: 11 }} onClick={() => setBalanceEdit(null)}>✕</button>
                        </span>
                      ) : (
                        <button className="btn btn-ghost" style={{ fontSize: 11 }}
                          onClick={() => setBalanceEdit({ provider, value: '' })}>
                          Update balance
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <div style={{ padding: '8px 12px', fontSize: 11, color: 'var(--text-muted)', borderTop: '1px solid var(--border)' }}>
            Type in your balance whenever you check the console or top up. CostWindow counts tracked spend down
            from it, shows how many days it lasts at your current burn rate, and flags any money that left your
            account without being tracked.
          </div>
        </div>
      </section>

    </div>
  )
}
