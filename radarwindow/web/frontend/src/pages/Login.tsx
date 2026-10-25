import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login } from '../api/auth'
import { useAuth } from '../contexts/AuthContext'

export default function Login() {
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)
  const { signIn } = useAuth()
  const navigate   = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await login(email, password)
      signIn(data.access_token, data.user_id, data.email, data.refresh_token)
      navigate('/dashboard')
    } catch {
      setError('Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100svh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
      <div className="card" style={{ width: 360 }}>
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontWeight: 700, fontSize: 18, color: 'var(--green)', letterSpacing: '0.05em', marginBottom: 4 }}>
            RADAR<span style={{ color: 'var(--text-muted)' }}>WINDOW</span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>The weekly intelligence brief for your niche</p>
        </div>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required />
          <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required />
          {error && <p className="error-msg">{error}</p>}
          <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: 4 }}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <p style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
          No account? <Link to="/register" style={{ color: 'var(--green)' }}>Register</Link>
          {' · '}
          <Link to="/pricing" style={{ color: 'var(--green)' }}>Pricing</Link>
        </p>
      </div>
    </div>
  )
}
