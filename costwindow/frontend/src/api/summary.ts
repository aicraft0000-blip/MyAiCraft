import api from './client'

export const getSummary = () =>
  api.get('/summary').then(r => r.data)

export const createManualEntry = (data: {
  label: string; provider: string; cost_usd: number;
  called_at: string; notes?: string;
}) => api.post('/manual-entry', data).then(r => r.data)

export interface ManualEntry {
  id: string
  label: string
  provider: string
  cost_usd: number
  called_at: string
  notes: string | null
}

export const listManualEntries = (): Promise<ManualEntry[]> =>
  api.get('/manual-entries').then(r => r.data)

export const updateManualEntry = (
  id: string,
  data: { cost_usd?: number; called_at?: string; notes?: string },
) => api.patch(`/manual-entry/${id}`, data).then(r => r.data)

export const deleteManualEntry = (id: string) =>
  api.delete(`/manual-entry/${id}`)
