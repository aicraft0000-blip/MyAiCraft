import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { createProcess } from "../api/processes"
import { getApiKeyInfo, getPlan } from "../api/auth"
import { MONTHLY_URL, YEARLY_URL, MONTHLY_CTA, YEARLY_CTA } from "../billing"

export default function AddProcess() {
  const [label,       setLabel]       = useState("")
  const [provider,    setProvider]    = useState("anthropic")
  const [description, setDescription] = useState("")
  const [error,       setError]       = useState("")
  const [created,     setCreated]     = useState<any>(null)
  const [copied,      setCopied]      = useState(false)
  const navigate = useNavigate()
  const qc       = useQueryClient()
  const { data: keyInfo } = useQuery({ queryKey: ["apikey"], queryFn: getApiKeyInfo })
  const { data: plan } = useQuery({ queryKey: ["plan"], queryFn: getPlan })
  const [capped, setCapped] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!/^[a-z0-9-]+$/.test(label)) { setError("Lowercase letters, numbers, and hyphens only"); return }
    try {
      const proc = await createProcess({ label, provider, description })
      qc.invalidateQueries({ queryKey: ["processes"] })
      setCreated(proc)
    } catch (err: any) {
      if (err?.response?.status === 403) setCapped(true)
      setError(err?.response?.data?.detail || "Failed to create process")
    }
  }

  const keyDisplay = keyInfo?.key_prefix ? (keyInfo.key_prefix + "...") : "cw_live_your_key"
  // Proxy-first: change one line (the base URL). No SDK, any language.
  const snippet = created
    ? "# Point your AI client at CostWindow — one line, no SDK.\n"
      + "# Killed / over-budget processes are refused before the provider is called.\n\n"
      + "client = anthropic.Anthropic(\n"
      + "    base_url=\"https://api.costwindow.com/proxy/anthropic/" + keyDisplay + "\",\n"
      + ")\n\n"
      + "# OpenAI: base_url=\"https://api.costwindow.com/proxy/openai/" + keyDisplay + "/v1\"\n"
      + "# Name this process with a header:  X-CostWindow-Label: " + label
    : null

  if (created) return (
    <div>
      <div className="page-header"><h1>Process Created</h1></div>
      <div className="card" style={{ maxWidth: 600 }}>
        <p style={{ marginBottom: 16 }}>
          <span className="num" style={{ color: "var(--green)" }}>OK</span>{" "}
          <strong>{label}</strong> is ready. Add this to your script:
        </p>
        {snippet && (
          <div style={{ position: "relative" }}>
            <pre className="code-block">{snippet}</pre>
            <button onClick={() => { navigator.clipboard.writeText(snippet); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
              className="btn btn-ghost" style={{ position: "absolute", top: 8, right: 8, fontSize: 11, padding: "3px 8px" }}>
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        )}
        <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate("/processes")}>
          View all processes
        </button>
      </div>
    </div>
  )

  return (
    <div>
      <div className="page-header"><h1>Add Process</h1></div>
      <div className="card" style={{ maxWidth: 480 }}>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontSize: 12, color: "var(--text-muted)" }}>Process Label</label>
            <input value={label} onChange={e => setLabel(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-"))}
              placeholder="e.g. quesi-horoscope" required />
            <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>Lowercase, hyphens only.</p>
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontSize: 12, color: "var(--text-muted)" }}>Provider</label>
            <select value={provider} onChange={e => setProvider(e.target.value)}>
              <option value="anthropic">Anthropic</option>
              <option value="openai">OpenAI</option>
              <option value="google">Google (Gemini)</option>
            </select>
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontSize: 12, color: "var(--text-muted)" }}>Description (optional)</label>
            <input value={description} onChange={e => setDescription(e.target.value)} placeholder="What does this process do?" />
          </div>
          {plan?.plan === "free" && !capped && (
            <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
              Free plan — {plan.free_process_limit} processes. Existing processes always keep tracking.
            </p>
          )}
          {error && !capped && <p style={{ color: "var(--red)", fontSize: 12 }}>{error}</p>}
          {capped && (
            <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 8, padding: "14px 18px" }}>
              <p style={{ margin: "0 0 10px", fontSize: 13, color: "#92400e" }}>
                You're on the free plan (2 processes). Upgrade to track unlimited processes.
              </p>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <a className="btn btn-primary" href={MONTHLY_URL} target="_blank" rel="noopener noreferrer">{MONTHLY_CTA}</a>
                <a className="btn" href={YEARLY_URL} target="_blank" rel="noopener noreferrer">{YEARLY_CTA}</a>
              </div>
            </div>
          )}
          <button type="submit" className="btn btn-primary">Create Process</button>
        </form>
      </div>
    </div>
  )
}
