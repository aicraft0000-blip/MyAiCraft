import { Outlet } from 'react-router-dom'
import TopBar from './TopBar'
import Sidebar from './Sidebar'

export default function Layout() {
  return (
    <div className="layout">
      <TopBar />
      <Sidebar />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
