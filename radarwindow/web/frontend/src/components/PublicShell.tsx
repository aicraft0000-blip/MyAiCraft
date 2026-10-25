import { Link } from 'react-router-dom'

export default function PublicShell({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ minHeight: '100svh', background: 'var(--bg)' }}>
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 24px', borderBottom: '1px solid var(--border)', background: 'var(--bg-card)' }}>
        <Link to="/p" style={{ textDecoration: 'none', fontWeight: 700, fontSize: 16, color: 'var(--green)', letterSpacing: '0.05em' }}>
          RADAR<span style={{ color: 'var(--text-muted)' }}>WINDOW</span>
        </Link>
        <nav style={{ display: 'flex', gap: 16, alignItems: 'center', fontSize: 13 }}>
          <Link to="/methodology" style={{ color: 'var(--text)', textDecoration: 'none' }}>Methodology</Link>
          <Link to="/pricing" style={{ color: 'var(--text)', textDecoration: 'none' }}>Pricing</Link>
          <Link to="/login" className="btn btn-ghost" style={{ fontSize: 12, padding: '4px 12px' }}>Sign in</Link>
        </nav>
      </header>
      <main style={{ maxWidth: 720, margin: '0 auto', padding: '40px 24px 80px' }}>
        {children}
      </main>
    </div>
  )
}
