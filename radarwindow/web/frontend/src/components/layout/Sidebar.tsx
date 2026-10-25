import { NavLink } from 'react-router-dom'

const links = [
  { to: '/dashboard', label: 'Briefs',    end: true },
  { to: '/archive',   label: 'Archive',   end: false },
  { to: '/niches',    label: 'Niches',    end: false },
  { to: '/settings',  label: 'Settings',  end: false },
]

export default function Sidebar() {
  return (
    <div className="sidebar">
      <div className="sidebar-label" style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', padding: '4px 12px 12px' }}>
        RadarWindow
      </div>
      {links.map(l => (
        <NavLink
          key={l.to}
          to={l.to}
          end={l.end}
          className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
        >
          {l.label}
        </NavLink>
      ))}
    </div>
  )
}
