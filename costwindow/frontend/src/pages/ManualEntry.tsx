import { useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { createManualEntry, listManualEntries, updateManualEntry, deleteManualEntry } from "../api/summary"
import type { ManualEntry as ManualEntryRow } from "../api/summary"
import { getProcesses } from "../api/processes"
import { MONTHLY_URL, YEARLY_URL, MONTHLY_CTA, YEARLY_CTA } from "../billing"

function EntryList() {
  const qc = useQueryClient()
  const { data: entries } = useQuery({ queryKey: ["manual-entries"], queryFn: listManualEntries })
  const [editingId, setEditingId] = useState<string | null>(null)
  const [edit, setEdit] = useState({ cost: "", date: "", notes: "" })

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["manual-entries"] })
    qc.invalidateQueries({ queryKey: ["processes"] })
    qc.invalidateQueries({ queryKey: ["summary"] })
  }

  const startEdit = (e: ManualEntryRow) => {
    setEditingId(e.id)
    setEdit({ cost: String(e.cost_usd), date: e.called_at.slice(0, 10), notes: e.notes || "" })
  }

  const saveEdit = async (id: string) => {
    await updateManualEntry(id, {
      cost_usd: parseFloat(edit.cost),
      called_at: new Date(edit.date).toISOString(),
      notes: edit.notes,
    })
    setEditingId(null)
    refresh()
  }

  if (!entries || entries.length === 0) return null

  return (
    <div style={{ marginTop: 28 }}>
      <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-muted)", marginBottom: 12,
        textTransform: "uppercase", letterSpacing: "0.08em" }}>
        Recent entries
      </h2>
      <div className="card card-table">
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              {["DATE", "PROCESS", "COST (USD)", "NOTES", ""].map((h, i) => (
                <th key={i} style={{ textAlign: "left", padding: "8px 12px", color: "var(--text-muted)", fontSize: 11, fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {entries.map(e => (
              editingId === e.id ? (
                <tr key={e.id} style={{ borderBottom: "1px solid var(--border)", background: "rgba(245,158,11,0.05)" }}>
                  <td style={{ padding: "8px 12px" }}>
                    <input type="date" value={edit.date} onChange={ev => setEdit(f => ({ ...f, date: ev.target.value }))} />
                  </td>
                  <td style={{ padding: "8px 12px", fontSize: 12, color: "var(--text-muted)" }}>{e.label}</td>
                  <td style={{ padding: "8px 12px" }}>
                    <input type="number" min="0" step="0.0001" value={edit.cost} style={{ width: 90 }}
                      onChange={ev => setEdit(f => ({ ...f, cost: ev.target.value }))} />
                  </td>
                  <td style={{ padding: "8px 12px" }}>
                    <input value={edit.notes} style={{ width: "100%" }}
                      onChange={ev => setEdit(f => ({ ...f, notes: ev.target.value }))} />
                  </td>
                  <td style={{ padding: "8px 12px", textAlign: "right", whiteSpace: "nowrap" }}>
                    <button className="btn btn-primary" style={{ fontSize: 11, marginRight: 6 }} onClick={() => saveEdit(e.id)}>Save</button>
                    <button className="btn btn-ghost" style={{ fontSize: 11 }} onClick={() => setEditingId(null)}>Cancel</button>
                  </td>
                </tr>
              ) : (
                <tr key={e.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "8px 12px", fontSize: 12, color: "var(--text-muted)" }}>{e.called_at.slice(0, 10)}</td>
                  <td style={{ padding: "8px 12px", fontSize: 13 }}>{e.label}
                    <span style={{ fontSize: 11, color: "var(--text-muted)" }}> · {e.provider}</span>
                  </td>
                  <td style={{ padding: "8px 12px" }}><span className="num">${e.cost_usd.toFixed(4)}</span></td>
                  <td style={{ padding: "8px 12px", fontSize: 12, color: "var(--text-muted)" }}>{e.notes || "—"}</td>
                  <td style={{ padding: "8px 12px", textAlign: "right", whiteSpace: "nowrap" }}>
                    <button className="btn btn-ghost" style={{ fontSize: 11 }} onClick={() => startEdit(e)}>Edit</button>
                    <button className="btn btn-ghost" style={{ fontSize: 11, color: "var(--text-muted)" }}
                      onClick={async () => { if (confirm("Delete this entry?")) { await deleteManualEntry(e.id); refresh() } }}>
                      Delete
                    </button>
                  </td>
                </tr>
              )
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function ManualEntry() {
  const qc              = useQueryClient()
  const { data: procs } = useQuery({ queryKey: ["processes"], queryFn: getProcesses })
  const [label,    setLabel]    = useState("")
  const [provider, setProvider] = useState("")
  const [cost,     setCost]     = useState("")
  const [date,     setDate]     = useState(new Date().toISOString().slice(0, 10))
  const [notes,    setNotes]    = useState("")
  const [done,     setDone]     = useState(false)
  const [error,    setError]    = useState("")
  const [capped,   setCapped]   = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      await createManualEntry({
        label,
        provider: provider || "manual",
        cost_usd: parseFloat(cost),
        called_at: new Date(date).toISOString(),
        notes: notes || undefined,
      })
      qc.invalidateQueries({ queryKey: ["processes"] })
      qc.invalidateQueries({ queryKey: ["summary"] })
      qc.invalidateQueries({ queryKey: ["manual-entries"] })
      setDone(true)
    } catch (err: any) {
      if (err?.response?.status === 403) setCapped(true)
      setError(err?.response?.data?.detail || "Failed to record entry")
    }
  }

  if (done) return (
    <div>
      <div className="page-header"><h1>Manual Entry</h1></div>
      <div className="card" style={{ maxWidth: 480 }}>
        <p style={{ color: "var(--green)", marginBottom: 16 }}>Entry recorded.</p>
        <button className="btn btn-primary" onClick={() => { setDone(false); setCost(""); setNotes("") }}>Add another</button>
      </div>
      <EntryList />
    </div>
  )

  return (
    <div>
      <div className="page-header"><h1>Manual Entry</h1></div>
      <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 20 }}>
        For tools like OpusClip or Blotato. Entries appear in all charts with a manual tag.
      </p>
      <div className="card" style={{ maxWidth: 480 }}>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontSize: 12, color: "var(--text-muted)" }}>Process</label>
            <input list="proc-list" value={label} onChange={e => setLabel(e.target.value)} placeholder="Select or type a label" required />
            <datalist id="proc-list">
              {(procs || []).map((p: any) => <option key={p.id} value={p.label} />)}
            </datalist>
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontSize: 12, color: "var(--text-muted)" }}>Provider / Tool</label>
            <input value={provider} onChange={e => setProvider(e.target.value)} placeholder="e.g. opusclip, blotato" />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontSize: 12, color: "var(--text-muted)" }}>Date</label>
            <input type="date" value={date} onChange={e => setDate(e.target.value)} required />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontSize: 12, color: "var(--text-muted)" }}>Cost (USD)</label>
            <input type="number" min="0" step="0.0001" value={cost} onChange={e => setCost(e.target.value)} placeholder="0.0000" required />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontSize: 12, color: "var(--text-muted)" }}>Notes (optional)</label>
            <input value={notes} onChange={e => setNotes(e.target.value)} placeholder="What was this for?" />
          </div>
          {error && !capped && <p style={{ color: "var(--red)", fontSize: 12 }}>{error}</p>}
          {capped && (
            <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 8, padding: "14px 18px" }}>
              <p style={{ margin: "0 0 10px", fontSize: 13, color: "#92400e" }}>
                {typeof error === "string" && error
                  ? error
                  : "You're on the free plan (2 processes). Upgrade to track unlimited processes."}
              </p>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <a className="btn btn-primary" href={MONTHLY_URL} target="_blank" rel="noopener noreferrer">{MONTHLY_CTA}</a>
                <a className="btn" href={YEARLY_URL} target="_blank" rel="noopener noreferrer">{YEARLY_CTA}</a>
              </div>
            </div>
          )}
          <button type="submit" className="btn btn-primary">Record Entry</button>
        </form>
      </div>
      <EntryList />
    </div>
  )
}
