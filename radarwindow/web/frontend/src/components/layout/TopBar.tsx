import { useAuth } from '../../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

export default function TopBar() {
  const { email, signOut } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="topbar">
      <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--green)', letterSpacing: '0.05em' }}>
        RADAR<span style={{ color: 'var(--text-muted)' }}>WINDOW</span>
      </span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{email}</span>
        <button
          className="btn btn-ghost"
          style={{ fontSize: 12, padding: '4px 10px' }}
          onClick={() => { signOut(); navigate('/login') }}
        >
          Sign out
        </button>
      </div>
    </div>
  )
}
