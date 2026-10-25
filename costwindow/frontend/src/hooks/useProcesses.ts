import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProcesses, toggleProcess, getProcessHistory } from '../api/processes'

export function useProcesses() {
  return useQuery({ queryKey: ['processes'], queryFn: getProcesses, refetchInterval: 60_000 })
}

export function useToggleProcess() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      toggleProcess(id, isActive),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['processes'] })
      qc.invalidateQueries({ queryKey: ['summary'] })
    },
  })
}

export function useProcessHistory(id: string) {
  return useQuery({ queryKey: ['history', id], queryFn: () => getProcessHistory(id) })
}
