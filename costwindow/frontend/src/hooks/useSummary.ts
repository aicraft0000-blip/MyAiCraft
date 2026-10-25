import { useQuery } from '@tanstack/react-query'
import { getSummary } from '../api/summary'

export interface SummaryData {
  total_cost_today: number
  total_cost_this_week: number
  total_cost_this_month: number
  most_expensive_process: { label: string; cost_usd: number } | null
  most_active_process: { label: string; call_count: number } | null
  cost_by_provider: Record<string, number>
  cost_by_day: { date: string; cost_usd: number }[]
  any_spikes: boolean
  spike_list: string[]
  subscriptions_monthly_gbp: number
  subscriptions_count: number
  kill_switches_active: number
}

export function useSummary() {
  return useQuery<SummaryData>({ queryKey: ['summary'], queryFn: getSummary, refetchInterval: 60_000 })
}
