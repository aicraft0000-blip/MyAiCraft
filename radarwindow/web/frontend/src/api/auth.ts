import { api } from './client'

export const login    = (email: string, password: string) =>
  api.post('/auth/login',    { email, password }).then(r => r.data)

export const register = (email: string, password: string) =>
  api.post('/auth/register', { email, password }).then(r => r.data)

export const getSettings    = () => api.get('/auth/settings').then(r => r.data)

export const suggestSources = (niche: string) =>
  api.post('/auth/settings/suggest-sources', { niche }).then(r => r.data)
export const updateSettings = (data: Record<string, string>) =>
  api.patch('/auth/settings', data).then(r => r.data)
