import { useState } from 'react'
import { Link } from 'react-router-dom'
import { register } from '../api/auth'

export default function Register() {
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState('')
  const [done,     setDone]     = useState(false)
  const [loading,  setLoading]  = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      await register(email, password)
      setDone(true)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  if (done) return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ width: 360, textAlign: 'center' }}>
        <h2 style={{ marginBottom: 12 }}>Check your email</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>
          We sent a confirmation link to {email}. Click it then sign in.
        </p>
        <Link to="/login" className="btn btn-primary" style={{ display: 'inline-block' }}>Back to login</Link>
      </div>
    </div>
  )

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ width: 360 }}>
        <div style={{ marginBottom: 24 }}>
          <h1 className="num" style={{ fontSize: 22, marginBottom: 4 }}>CostWindow</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            Create your free account — 2 processes tracked, every feature, no card.
            Subscribers register here too.
          </p>
        </div>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required />
          <input type="password" placeholder="Password (min 8 chars)" value={password} onChange={e => setPassword(e.target.value)} minLength={8} required />
          {error && (
            <p style={{ color: 'var(--red)', fontSize: 12 }}>{error}</p>
          )}
          <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: 4 }}>
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>
        <p style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
          Have an account? <Link to="/login" style={{ color: 'var(--amber)' }}>Sign in</Link>
        </p>
      </div>
    </div>
  )
}
