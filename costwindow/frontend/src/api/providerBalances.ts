import api from './client'

export interface ProviderBalance {
  id: string
  provider: string
  balance_usd: number | null
  used_usd: number | null
  granted_usd: number | null
  fetched_at: string
  estimated_balance_usd?: number | null
  daily_burn_usd?: number
  runway_days?: number | null
  reconciliation?: {
    balance_drop_usd: number
    untracked_spend_usd: number | null
    alert: boolean
  } | null
}

export interface ProviderBalancesResponse {
  balances: ProviderBalance[]
  openai_configured: boolean
}

export const getProviderBalances = (): Promise<ProviderBalancesResponse> =>
  api.get('/provider-balances/latest').then(r => r.data)

export const refreshProviderBalances = (): Promise<{ refreshed: unknown[] }> =>
  api.post('/provider-balances/refresh').then(r => r.data)

export const recordManualBalance = (provider: string, balanceUsd: number) =>
  api.post('/provider-balances/manual', { provider, balance_usd: balanceUsd }).then(r => r.data)
