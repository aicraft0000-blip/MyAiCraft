import { api } from './client'

export interface Niche {
  id: string
  label: string
  niche: string
  subreddits: string
  github_topics: string
  web_queries: string
  rss_feeds: string
  avoid_words: string
  notify_email: string | null
  active: boolean
  created_at: string
}

export type NicheInput = Partial<Omit<Niche, 'id' | 'created_at'>>

export const listNiches  = (): Promise<Niche[]> => api.get('/auth/niches').then(r => r.data)

export const createNiche = (data: NicheInput): Promise<Niche> =>
  api.post('/auth/niches', data).then(r => r.data)

export const updateNiche = (id: string, data: NicheInput) =>
  api.patch(`/auth/niches/${id}`, data).then(r => r.data)

export const deleteNiche = (id: string) =>
  api.delete(`/auth/niches/${id}`).then(r => r.data)
