import { useState, useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useSummary } from '../../hooks/useSummary'
import { useSettings } from '../../hooks/useSettings'
import { useCurrency } from '../../contexts/CurrencyContext'
import { useAuth } from '../../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

const SCAN_PROMPT = `Scan my secrets and env files, identify everything with a monetary value — API keys, subscription tokens, cron jobs, and session tools. Add any new findings to my CostWindow dashboard.`

function CopyBlock({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <code style={{ flex: 1, background: 'var(--bg-secondary, #1a1a1a)', border: '1px solid var(--border)', borderRadius: 6,
          padding: '10px 12px', fontSize: 12, lineHeight: 1.6, color: 'var(--text)', wordBreak: 'break-all',
          display: 'block', whiteSpace: 'pre-wrap' }}>
          {value}
        </code>
        <button onClick={copy} className="btn btn-ghost"
          style={{ fontSize: 11, padding: '8px 12px', whiteSpace: 'nowrap', flexShrink: 0 }}>
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
    </div>
  )
}

export default function TopBar() {
  const { data, isFetching }   = useSummary()
  const { data: appSettings }  = useSettings()
  const { format }             = useCurrency()
  const { signOut, email }     = useAuth()
  const navigate               = useNavigate()
  const qc                     = useQueryClient()
  const [showModal, setShowModal]   = useState(false)
  const [showBell, setShowBell]     = useState(false)
  const bellRef                     = useRef<HTMLDivElement>(null)

  const notificationsOn = appSettings?.notifications_enabled !== false
  const hasSpikes = notificationsOn && !!data?.any_spikes

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) {
        setShowBell(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['summary'] })
    qc.invalidateQueries({ queryKey: ['processes'] })
    qc.invalidateQueries({ queryKey: ['subscriptions'] })
  }

  const terminalCmd = `python3 ~/.costwindow/scanner.py`

  return (
    <>
      <div className="topbar">
        <div className="topbar-left">
          <span className="num topbar-brand" style={{ fontWeight: 600, fontSize: 15, color: 'var(--amber)' }}>
            CostWindow
          </span>
          {data && (
            <span className="topbar-totals" style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              Today: <span className="num" style={{ color: 'var(--text)' }}>{format(data.total_cost_today)}</span>
              {' | '}
              Month: <span className="num" style={{ color: 'var(--text)' }}>{format(data.total_cost_this_month)}</span>
              {' | '}
              Subscriptions: <span className="num" style={{ color: 'var(--text)' }}>
                £{(data.subscriptions_monthly_gbp || 0).toFixed(2)}/mo
              </span>
              {(data.kill_switches_active ?? 0) > 0 && (
                <span style={{ color: 'var(--red)', marginLeft: 8 }}>
                  ⚠ {data.kill_switches_active} kill switch{data.kill_switches_active !== 1 ? 'es' : ''} active
                </span>
              )}
            </span>
          )}
        </div>
        <div className="topbar-right">
          {notificationsOn && (
            <div ref={bellRef} style={{ position: 'relative' }}>
              <button className="btn btn-ghost" style={{ fontSize: 14, padding: '4px 10px' }}
                onClick={() => setShowBell(v => !v)}>
                🔔
                {hasSpikes && (
                  <span style={{
                    position: 'absolute', top: 2, right: 2,
                    width: 8, height: 8, borderRadius: '50%',
                    background: 'var(--red)', display: 'block',
                  }} />
                )}
              </button>
              {showBell && (
                <div style={{
                  position: 'absolute', top: '100%', right: 0, marginTop: 6,
                  background: 'var(--bg-card, #1e1e1e)', border: '1px solid var(--border)',
                  borderRadius: 8, padding: 16, minWidth: 220, zIndex: 200,
                }} onClick={e => e.stopPropagation()}>
                  {hasSpikes ? (
                    <>
                      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: 'var(--red)' }}>
                        ⚠ Cost spike detected
                      </div>
                      {(data?.spike_list ?? []).map(label => (
                        <div key={label} style={{ fontSize: 12, color: 'var(--text-muted)', padding: '2px 0' }}>
                          • {label}
                        </div>
                      ))}
                    </>
                  ) : (
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>No alerts — all clear.</div>
                  )}
                </div>
              )}
            </div>
          )}
          <button className="btn btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }}
            onClick={refresh} disabled={isFetching}>
            {isFetching ? '↻ Refreshing…' : '↻ Refresh'}
          </button>
          <button className="btn btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => setShowModal(true)}>
            🔍 Scan for Secrets
          </button>
          <span className="topbar-email" style={{ color: 'var(--text-muted)', fontSize: 12 }}>{email}</span>
          <button className="btn btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }}
            onClick={() => { signOut(); navigate('/login') }}>
            Sign out
          </button>
        </div>
      </div>

      {showModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}
          onClick={() => setShowModal(false)}>
          <div style={{ background: 'var(--bg-card, #1e1e1e)', border: '1px solid var(--border)',
            borderRadius: 12, padding: 28, maxWidth: 560, width: '100%' }}
            onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h3 style={{ fontSize: 15, fontWeight: 600 }}>🔍 Scan for Secrets</h3>
              <button className="btn btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }}
                onClick={() => setShowModal(false)}>✕ Close</button>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20, lineHeight: 1.6 }}>
              Run this in your terminal to scan your secrets files and add any new services to CostWindow.
            </p>
            <CopyBlock label="Terminal command" value={terminalCmd} />
            <div style={{ borderTop: '1px solid var(--border)', margin: '20px 0' }} />
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12, lineHeight: 1.6 }}>
              Or paste this into your AI CLI (Claude Code, Codex, OpenClaw, Hermes, etc.):
            </p>
            <CopyBlock label="AI CLI prompt" value={SCAN_PROMPT} />
          </div>
        </div>
      )}
    </>
  )
}
