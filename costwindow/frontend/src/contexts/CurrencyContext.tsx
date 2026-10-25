import React, { createContext, useContext, useState } from 'react'

// Static exchange rate USD → GBP. Replace with a live rate API post-MVP.
const USD_TO_GBP = 0.79

interface CurrencyContextValue {
  currency: 'GBP' | 'USD'
  setCurrency: (c: 'GBP' | 'USD') => void
  format: (usd: number) => string
}

const CurrencyContext = createContext<CurrencyContextValue | null>(null)

export function CurrencyProvider({ children }: { children: React.ReactNode }) {
  const [currency, setCurrencyState] = useState<'GBP' | 'USD'>(
    (localStorage.getItem('cw_currency') as 'GBP' | 'USD') || 'GBP'
  )

  const format = (usd: number): string => {
    if (currency === 'GBP') return '£' + (usd * USD_TO_GBP).toFixed(4)
    return '$' + usd.toFixed(4)
  }

  const setCurrency = (c: 'GBP' | 'USD') => {
    localStorage.setItem('cw_currency', c)
    setCurrencyState(c)
  }

  return (
    <CurrencyContext.Provider value={{ currency, setCurrency, format }}>
      {children}
    </CurrencyContext.Provider>
  )
}

export function useCurrency() {
  const ctx = useContext(CurrencyContext)
  if (!ctx) throw new Error('useCurrency must be inside CurrencyProvider')
  return ctx
}
