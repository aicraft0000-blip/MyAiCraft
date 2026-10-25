import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { getApiKeyInfo, generateApiKey, updateSettings, getPlan } from "../api/auth"
import { useSettings } from "../hooks/useSettings"
import { useCurrency } from "../contexts/CurrencyContext"
import { MONTHLY_URL, YEARLY_URL, MONTHLY_CTA, YEARLY_CTA } from "../billing"

export default function Settings() {
  const qc = useQueryClient()
  const { currency, setCurrency } = useCurrency()
  const [newKey,    setNewKey]    = useState<string | null>(null)
  const [keyCopied, setKeyCopied] = useState(false)

  const { data: keyInfo }      = useQuery({ queryKey: ["apikey"], queryFn: getApiKeyInfo })
  const { data: userSettings } = useSettings()
  const { data: plan }         = useQuery({ queryKey: ["plan"], queryFn: getPlan })

  const { mutate: regen, isPending: regenLoading } = useMutation({
    mutationFn: generateApiKey,
    onSuccess: (data) => { setNewKey(data.api_key); qc.invalidateQueries({ queryKey: ["apikey"] }) },
  })
  const { mutate: saveSettings } = useMutation({
    mutationFn: updateSettings,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  })

  const isFree = !plan || plan.plan === "free"
  const planLabel = plan?.plan === "yearly" ? "Yearly" : plan?.plan === "monthly" ? "Monthly" : "Free"

  return (
    <div>
      <div className="page-header"><h1>Settings</h1></div>
      <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 560 }}>

        <div className="card">
          <div className="stat-label" style={{ marginBottom: 12 }}>Plan</div>
          {isFree ? (
            <>
              <p style={{ fontSize: 13, marginBottom: 10 }}>
                Free — {plan?.free_process_limit ?? 2} processes · every feature. Upgrade for unlimited processes.
              </p>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <a className="btn btn-primary" href={MONTHLY_URL} target="_blank" rel="noopener noreferrer">{MONTHLY_CTA}</a>
                <a className="btn" href={YEARLY_URL} target="_blank" rel="noopener noreferrer">{YEARLY_CTA}</a>
              </div>
            </>
          ) : (
            <p style={{ fontSize: 13 }}>
              {planLabel} — unlimited processes. Every feature included.
            </p>
          )}
        </div>

        <div className="card">
          <div className="stat-label" style={{ marginBottom: 12 }}>CostWindow API Key</div>
          {newKey ? (
            <div>
              <p style={{ color: "var(--amber)", fontSize: 12, marginBottom: 8 }}>Save this key now — it will not be shown again.</p>
              <div style={{ position: "relative" }}>
                <input readOnly value={newKey} style={{ fontFamily: "var(--font-num)", fontSize: 12 }} />
                <button onClick={() => { navigator.clipboard.writeText(newKey); setKeyCopied(true) }}
                  className="btn btn-ghost" style={{ position: "absolute", right: 4, top: 4, fontSize: 11, padding: "3px 8px" }}>
                  {keyCopied ? "Copied" : "Copy"}
                </button>
              </div>
            </div>
          ) : keyInfo?.has_key ? (
            <p style={{ fontSize: 13 }}>
              Prefix: <span className="num">{keyInfo.key_prefix}...</span>
              {keyInfo.last_used_at && (
                <span style={{ color: "var(--text-muted)", marginLeft: 12, fontSize: 12 }}>
                  Last used: {new Date(keyInfo.last_used_at).toLocaleDateString()}
                </span>
              )}
            </p>
          ) : (
            <p style={{ color: "var(--text-muted)", fontSize: 13 }}>No API key generated yet.</p>
          )}
          <button className="btn btn-ghost" style={{ marginTop: 12, fontSize: 13 }}
            onClick={() => regen()} disabled={regenLoading}>
            {regenLoading ? "Generating..." : keyInfo?.has_key ? "Regenerate key" : "Generate key"}
          </button>
        </div>

        <div className="card">
          <div className="stat-label" style={{ marginBottom: 12 }}>Display Currency</div>
          <div style={{ display: "flex", gap: 8 }}>
            {(["GBP", "USD"] as const).map(c => (
              <button key={c} className={"btn " + (currency === c ? "btn-primary" : "btn-ghost")}
                onClick={() => { setCurrency(c); saveSettings({ currency: c }) }}>
                {c === "GBP" ? "GBP" : "USD"}
              </button>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="stat-label" style={{ marginBottom: 12 }}>Spike Alert Threshold</div>
          <p style={{ color: "var(--text-muted)", fontSize: 12, marginBottom: 10 }}>Alert when cost is this many times the 7-day average.</p>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input type="number" min="1.1" max="10" step="0.5"
              defaultValue={userSettings?.spike_threshold || 2}
              style={{ width: 80 }}
              onBlur={e => saveSettings({ spike_threshold: parseFloat(e.target.value) })} />
            <span style={{ color: "var(--text-muted)", fontSize: 13 }}>x average</span>
          </div>
        </div>

        <div className="card">
          <div className="stat-label" style={{ marginBottom: 8 }}>Spike Notifications</div>
          <p style={{ color: "var(--text-muted)", fontSize: 12, marginBottom: 12 }}>
            Show a notification in the dashboard when a cost spike is detected.
          </p>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button
              className={"btn " + (userSettings?.notifications_enabled !== false ? "btn-primary" : "btn-ghost")}
              onClick={() => saveSettings({ notifications_enabled: true })}>
              On
            </button>
            <button
              className={"btn " + (userSettings?.notifications_enabled === false ? "btn-primary" : "btn-ghost")}
              onClick={() => saveSettings({ notifications_enabled: false })}>
              Off
            </button>
            <span style={{ color: "var(--text-muted)", fontSize: 12 }}>
              {userSettings?.notifications_enabled !== false ? "Notifications enabled" : "Notifications disabled"}
            </span>
          </div>
        </div>

      </div>
    </div>
  )
}
