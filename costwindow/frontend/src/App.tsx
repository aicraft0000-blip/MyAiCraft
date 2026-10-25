import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { CurrencyProvider } from './contexts/CurrencyContext'
import Layout from './components/layout/Layout'
import Landing from './pages/Landing'
import HowItWorks from './pages/HowItWorks'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Processes from './pages/Processes'
import ProcessDetail from './pages/ProcessDetail'
import AddProcess from './pages/AddProcess'
import Settings from './pages/Settings'
import ManualEntry from './pages/ManualEntry'
import Subscriptions from './pages/Subscriptions'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <AuthProvider>
      <CurrencyProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/"             element={<Landing />} />
            <Route path="/how-it-works" element={<HowItWorks />} />
            <Route path="/login"        element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
              <Route path="dashboard"     element={<Dashboard />} />
              <Route path="processes"     element={<Processes />} />
              <Route path="processes/:id" element={<ProcessDetail />} />
              <Route path="add-process"   element={<AddProcess />} />
              <Route path="settings"      element={<Settings />} />
              <Route path="manual-entry"  element={<ManualEntry />} />
              <Route path="subscriptions" element={<Subscriptions />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </CurrencyProvider>
    </AuthProvider>
  )
}
