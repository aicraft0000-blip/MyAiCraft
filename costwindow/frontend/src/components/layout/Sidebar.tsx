import { NavLink } from 'react-router-dom'

const links = [
  { to: '/',               label: 'Dashboard',     end: true },
  { to: '/processes',      label: 'Processes',     end: false },
  { to: '/add-process',    label: 'Add Process',   end: false },
  { to: '/manual-entry',   label: 'Manual Entry',  end: false },
  { to: '/subscriptions',  label: 'Subscriptions', end: false },
  { to: '/settings',       label: 'Settings',      end: false },
]

export default function Sidebar() {
  return (
    <div className="sidebar">
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
