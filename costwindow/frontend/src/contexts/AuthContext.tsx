import React, { createContext, useContext, useState } from 'react'

interface AuthState {
  token: string | null
  userId: string | null
  email: string | null
}

interface AuthContextValue extends AuthState {
  signIn: (token: string, userId: string, email: string, refreshToken?: string) => void
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token:  localStorage.getItem('cw_token'),
    userId: localStorage.getItem('cw_user_id'),
    email:  localStorage.getItem('cw_email'),
  })

  const signIn = (token: string, userId: string, email: string, refreshToken?: string) => {
    localStorage.setItem('cw_token',   token)
    localStorage.setItem('cw_user_id', userId)
    localStorage.setItem('cw_email',   email)
    if (refreshToken) localStorage.setItem('cw_refresh_token', refreshToken)
    setState({ token, userId, email })
  }

  const signOut = () => {
    localStorage.removeItem('cw_token')
    localStorage.removeItem('cw_user_id')
    localStorage.removeItem('cw_email')
    localStorage.removeItem('cw_refresh_token')
    setState({ token: null, userId: null, email: null })
  }

  return (
    <AuthContext.Provider value={{ ...state, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
