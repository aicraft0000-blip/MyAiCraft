import { useParams, useNavigate } from "react-router-dom"
import { useProcessHistory, useProcesses } from "../hooks/useProcesses"
import { useCurrency } from "../contexts/CurrencyContext"
import { BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts"

export default function ProcessDetail() {
  const { id }            = useParams<{ id: string }>()
  const navigate          = useNavigate()
  const { data: history } = useProcessHistory(id!)
  const { data: procs }   = useProcesses()
  const { format }        = useCurrency()

  const proc       = procs?.find((p: any) => p.id === id)
  const stats      = history?.history || []
  const totalCost  = stats.reduce((s: number, d: any) => s + d.cost_usd, 0)
  const totalCalls = stats.reduce((s: number, d: any) => s + d.call_count, 0)
  const avgPerCall = totalCalls > 0 ? totalCost / totalCalls : 0

  return (
    <div>
      <div className="page-header">
        <div>
          <button onClick={() => navigate(-1)} style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 8, display: "block" }}>
            Back
          </button>
          <h1 className="num">{proc?.label || id}</h1>
        </div>
      </div>
      <div className="dashboard-grid" style={{ marginBottom: 20 }}>
        <div className="card"><div className="stat-label">30-day Total</div><div className="stat-value num">{format(totalCost)}</div></div>
        <div className="card"><div className="stat-label">Total Calls (30d)</div><div className="stat-value num">{totalCalls}</div></div>
        <div className="card"><div className="stat-label">Avg Cost / Call</div><div className="stat-value num">{format(avgPerCall)}</div></div>
      </div>
      <div className="card">
        <div className="stat-label" style={{ marginBottom: 16 }}>Daily Cost - Last 30 Days</div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={stats}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="date" tick={{ fill: "var(--text-muted)", fontSize: 10 }} tickFormatter={(d: string) => d.slice(5)} />
            <YAxis tick={{ fill: "var(--text-muted)", fontSize: 10 }} width={60} />
            <Tooltip
              contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
              formatter={(v: unknown) => format(v as number)}
            />
            <Bar dataKey="cost_usd" fill="var(--amber)" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
