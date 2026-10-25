import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchSubscriptions,
  createSubscription,
  updateSubscription,
  deleteSubscription,
} from '../api/subscriptions'
import type { SubscriptionCreate, SubscriptionUpdate } from '../api/subscriptions'

export function useSubscriptions() {
  const qc = useQueryClient()
  const { data = [], isLoading, error } = useQuery({
    queryKey: ['subscriptions'],
    queryFn: fetchSubscriptions,
    refetchInterval: 60_000,
  })

  const addMutation = useMutation({
    mutationFn: createSubscription,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscriptions'] }),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      updateSubscription(id, { is_active }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['subscriptions'] })
      qc.invalidateQueries({ queryKey: ['summary'] })
    },
  })

  const removeMutation = useMutation({
    mutationFn: deleteSubscription,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscriptions'] }),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: SubscriptionUpdate }) =>
      updateSubscription(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['subscriptions'] })
      qc.invalidateQueries({ queryKey: ['summary'] })
    },
  })

  return {
    data,
    isLoading,
    error: error instanceof Error ? error.message : error ? String(error) : null,
    add: (sub: SubscriptionCreate) => addMutation.mutateAsync(sub),
    toggle: async (id: string, is_active: boolean) => { await toggleMutation.mutateAsync({ id, is_active }) },
    remove: async (id: string) => { await removeMutation.mutateAsync(id) },
    update: async (id: string, data: SubscriptionUpdate) => { await updateMutation.mutateAsync({ id, data }) },
  }
}
