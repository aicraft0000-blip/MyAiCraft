import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Layout from './components/layout/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import BriefDetail from './pages/BriefDetail'
import Settings from './pages/Settings'
import Niches from './pages/Niches'
import Archive from './pages/Archive'
import PublicBriefs from './pages/PublicBriefs'
import PublicBrief from './pages/PublicBrief'
import Pricing from './pages/Pricing'
import Methodology from './pages/Methodology'
import Landing from './pages/Landing'

const qc = new QueryClient()

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

function RootRedirect() {
  const { token } = useAuth()
  return token ? <Navigate to="/dashboard" replace /> : <Landing />
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/"         element={<RootRedirect />} />
            <Route path="/login"    element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/p"        element={<PublicBriefs />} />
            <Route path="/p/:slug"  element={<PublicBrief />} />
            <Route path="/pricing"  element={<Pricing />} />
            <Route path="/methodology" element={<Methodology />} />
            <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
              <Route path="dashboard"       element={<Dashboard />} />
              <Route path="briefs/:id"      element={<BriefDetail />} />
              <Route path="archive"         element={<Archive />} />
              <Route path="niches"          element={<Niches />} />
              <Route path="settings"        element={<Settings />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
