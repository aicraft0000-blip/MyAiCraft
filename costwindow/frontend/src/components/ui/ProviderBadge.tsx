export default function ProviderBadge({ provider }: { provider: string }) {
  const cls = provider === "anthropic" ? "badge-anthropic" : provider === "openai" ? "badge-openai" : "badge-manual"
  return <span className={"badge " + cls}>{provider}</span>
}
