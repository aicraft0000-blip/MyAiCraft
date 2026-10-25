import { api } from './client'

export interface QaFinding {
  code: string
  severity: string
  message: string
  auto_fixed?: boolean
}

export interface QaReport {
  id: string
  niche_id: string | null
  niche_label: string
  status: 'ok' | 'attention'
  on_niche_pct: number | null
  findings: QaFinding[]
  summary: string
  created_at: string
}

// Latest self-QA run, one report per niche — the dashboard's confirmation
// that the recurring alignment check ran.
export const latestQa = (): Promise<QaReport[]> => api.get('/qa/latest').then(r => r.data)
