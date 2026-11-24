import { useQuery } from '@tanstack/react-query'

import type { HourlyProcessingStatus } from '@/lib/processing-status'

/** Hourly service metrics behind `/api/status`. */
export function useProcessingStatus() {
  return useQuery<HourlyProcessingStatus>({
    queryKey: ['processing-status-hourly'],
    queryFn: async () => {
      const response = await fetch('/api/status')
      if (!response.ok) throw new Error('Processing status unavailable')
      return response.json()
    },
    staleTime: 60_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: false,
    retry: false,
  })
}
