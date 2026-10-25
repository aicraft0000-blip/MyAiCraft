import { useNavigate } from "react-router-dom"
import { useProcesses, useToggleProcess } from "../hooks/useProcesses"
import { useCurrency } from "../contexts/CurrencyContext"
import KillSwitch from "../components/ui/KillSwitch"
import ProviderBadge from "../components/ui/ProviderBadge"

function statusLabel(p: any): [string, string] {
  if (!p.is_active)  return ["DISABLED", "status-disabled"]
  if (p.spike_alert) return ["SPIKING",  "status-spiking"]
  return ["Active", "status-active"]
}

export default function Processes() {
  const { data: processes, isLoading } = useProcesses()
  const { mutateAsync: toggle }        = useToggleProcess()
  const { format }                     = useCurrency()
  const navigate                       = useNavigate()

  if (isLoading) return <div style={{ color: "var(--text-muted)", padding: 40 }}>Loading...</div>

  return (
    <div>
      <div className="page-header">
        <h1>Processes</h1>
        <button className="btn btn-primary" onClick={() => navigate("/add-process")}>+ Add Process</button>
      </div>
      <div className="card card-table" style={{ padding: 0 }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Label</th><th>Provider</th><th>Model</th>
              <th>Today</th><th>This Month</th><th>Last Called</th>
              <th>Status</th><th>Kill</th>
            </tr>
          </thead>
          <tbody>
            {(processes || []).map((p: any) => {
              const [statusText, statusClass] = statusLabel(p)
              return (
                <tr key={p.id} className={!p.is_active ? "disabled-row" : ""}
                  onClick={() => navigate("/processes/" + p.id)}>
                  <td style={{ fontFamily: "var(--font-num)", fontWeight: 500 }}>{p.label}</td>
                  <td><ProviderBadge provider={p.provider} /></td>
                  <td style={{ color: "var(--text-muted)", fontSize: 12 }}>{p.last_model || "—"}</td>
                  <td className="num">{format(p.today_cost_usd)}</td>
                  <td className="num">{format(p.this_month_cost_usd)}</td>
                  <td style={{ color: "var(--text-muted)", fontSize: 12 }}>
                    {p.last_called_at ? new Date(p.last_called_at).toLocaleString("en-GB", { timeStyle: "short", dateStyle: "short" }) : "—"}
                  </td>
                  <td><span className={statusClass} style={{ fontSize: 12, fontWeight: 600 }}>{statusText}</span></td>
                  <td><KillSwitch processId={p.id} label={p.label} isActive={p.is_active}
                    onToggle={(id, active) => toggle({ id, isActive: active })} /></td>
                </tr>
              )
            })}
            {!processes?.length && (
              <tr><td colSpan={8} style={{ textAlign: "center", color: "var(--text-muted)", padding: 32 }}>
                No processes yet. <a href="/add-process" style={{ color: "var(--amber)" }}>Add your first process.</a>
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
