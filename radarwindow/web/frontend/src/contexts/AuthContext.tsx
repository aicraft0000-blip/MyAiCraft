import { createContext, useContext, useState } from 'react'

interface AuthState {
  token:  string | null
  userId: string | null
  email:  string | null
}

interface AuthContextValue extends AuthState {
  signIn:  (token: string, userId: string, email: string, refreshToken?: string) => void
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token:  localStorage.getItem('rw_token'),
    userId: localStorage.getItem('rw_user_id'),
    email:  localStorage.getItem('rw_email'),
  })

  const signIn = (token: string, userId: string, email: string, refreshToken?: string) => {
    localStorage.setItem('rw_token',   token)
    localStorage.setItem('rw_user_id', userId)
    localStorage.setItem('rw_email',   email)
    if (refreshToken) localStorage.setItem('rw_refresh_token', refreshToken)
    setState({ token, userId, email })
  }

  const signOut = () => {
    ['rw_token', 'rw_user_id', 'rw_email', 'rw_refresh_token'].forEach(k => localStorage.removeItem(k))
    setState({ token: null, userId: null, email: null })
  }

  return <AuthContext.Provider value={{ ...state, signIn, signOut }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}
