import { useState } from "react"

interface Props {
  processId: string
  label: string
  isActive: boolean
  onToggle: (id: string, isActive: boolean) => Promise<void>
}

export default function KillSwitch({ processId, label, isActive, onToggle }: Props) {
  const [confirming, setConfirming] = useState(false)
  const [loading,    setLoading]    = useState(false)

  async function handleClick(e: React.MouseEvent) {
    e.stopPropagation()
    if (isActive) { setConfirming(true); return }
    setLoading(true)
    try { await onToggle(processId, true) } finally { setLoading(false) }
  }

  async function confirmDisable(e: React.MouseEvent) {
    e.stopPropagation()
    setConfirming(false)
    setLoading(true)
    try { await onToggle(processId, false) } finally { setLoading(false) }
  }

  return (
    <>
      <button
        className={"kill-switch " + (isActive ? "active" : "disabled")}
        onClick={handleClick}
        disabled={loading}
        title={isActive ? "Click to disable" : "Click to enable"}
        style={{ opacity: loading ? 0.6 : 1 }}
      >
        <div className="kill-switch-thumb" />
      </button>

      {confirming && (
        <div className="modal-overlay" onClick={() => setConfirming(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Stop {label}?</h3>
            <p>This will immediately block all API calls. The SDK will raise CostWindowProcessDisabledError.</p>
            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={e => { e.stopPropagation(); setConfirming(false) }}>Cancel</button>
              <button className="btn btn-danger" onClick={confirmDisable}>Stop process</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
