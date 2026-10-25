import api from './client'

export const login = (email: string, password: string) =>
  api.post('/auth/login', { email, password }).then(r => r.data)

export const register = (email: string, password: string) =>
  api.post('/auth/register', { email, password }).then(r => r.data)

export const getPlan = (): Promise<{ plan: string; free_process_limit: number }> =>
  api.get('/auth/plan').then(r => r.data)

export const getApiKeyInfo = () =>
  api.get('/auth/apikey/info').then(r => r.data)

export const generateApiKey = () =>
  api.post('/auth/apikey/generate').then(r => r.data)

export const getSettings = () =>
  api.get('/auth/settings').then(r => r.data)

export const updateSettings = (data: Record<string, unknown>) =>
  api.patch('/auth/settings', data).then(r => r.data)
