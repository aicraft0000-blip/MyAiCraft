import { useQuery } from '@tanstack/react-query'
import { getSettings } from '../api/auth'

export function useSettings() {
  return useQuery({ queryKey: ['settings'], queryFn: getSettings })
}
