import { api } from './client'

export const listDigests = () => api.get('/digests').then(r => r.data)
