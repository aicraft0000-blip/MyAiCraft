import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProviderBalances, refreshProviderBalances } from '../api/providerBalances'

export function useProviderBalances() {
  return useQuery({
    queryKey: ['provider-balances'],
    queryFn: getProviderBalances,
  })
}

export function useRefreshProviderBalances() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: refreshProviderBalances,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['provider-balances'] }),
  })
}
