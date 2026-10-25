import api from './client'

export const getProcesses = () =>
  api.get('/processes').then(r => r.data)

export const createProcess = (data: { label: string; provider: string; description?: string }) =>
  api.post('/processes', data).then(r => r.data)

export const toggleProcess = (id: string, isActive: boolean) =>
  api.patch(`/processes/${id}`, { is_active: isActive, confirm: true }).then(r => r.data)

export const updateProcessBudget = (
  id: string,
  fields: { budget_usd_month?: number; budget_action?: 'warn' | 'block'; cost_driver?: 'scheduled' | 'demand' },
) =>
  api.patch(`/processes/${id}`, fields).then(r => r.data)

export const getProcessHistory = (id: string) =>
  api.get(`/processes/${id}/history`).then(r => r.data)
