import axios from 'axios'

// Plain client for public pages — never attaches auth tokens, never triggers
// the 401-refresh redirect in the intercepted client.
const pub = axios.create({ baseURL: '/api' })

export const listPublicBriefs = () => pub.get('/public/briefs').then(r => r.data)
export const getPublicBrief   = (slug: string) => pub.get(`/public/briefs/${slug}`).then(r => r.data)
