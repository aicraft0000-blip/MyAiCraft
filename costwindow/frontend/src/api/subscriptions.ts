import api from './client'

export interface Subscription {
  id: string
  name: string
  cost_gbp: number
  renewal_day: number | null
  cancel_url: string | null
  is_active: boolean
  created_at: string
}

export interface SubscriptionCreate {
  name: string
  cost_gbp: number
  renewal_day?: number
  cancel_url?: string
}

export interface SubscriptionUpdate {
  name?: string
  cost_gbp?: number
  renewal_day?: number
  cancel_url?: string
  is_active?: boolean
}

export async function fetchSubscriptions(): Promise<Subscription[]> {
  const res = await api.get('/subscriptions/')
  return res.data
}

export async function createSubscription(data: SubscriptionCreate): Promise<Subscription> {
  const res = await api.post('/subscriptions/', data)
  return res.data
}

export async function updateSubscription(id: string, data: SubscriptionUpdate): Promise<Subscription> {
  const res = await api.patch(`/subscriptions/${id}`, data)
  return res.data
}

export async function deleteSubscription(id: string): Promise<void> {
  await api.delete(`/subscriptions/${id}`)
}
