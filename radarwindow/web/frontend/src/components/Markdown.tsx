export function renderMarkdown(md: string) {
  // Simple markdown → HTML for display (no external lib needed for this use case)
  if (!md) return ''  // guard: a null/empty body must never throw and blank the page
  return md
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/(^|[\s])(https?:\/\/[^\s<]+)/gm, '$1<a href="$2" target="_blank" rel="noopener">$2</a>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[hul])(.+)$/gm, '<p>$1</p>')
}

export default function Markdown({ md }: { md: string }) {
  return <div className="brief-content" dangerouslySetInnerHTML={{ __html: renderMarkdown(md) }} />
}
