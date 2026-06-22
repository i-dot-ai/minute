'use client'

import { listTranscriptionsTranscriptionsGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { keepPreviousData, useQuery } from '@tanstack/react-query'

export function useTranscriptions({
  page,
  pageSize,
}: {
  page: number
  pageSize: number
}) {
  return useQuery({
    ...listTranscriptionsTranscriptionsGetOptions({
      query: { page, page_size: pageSize },
    }),
    refetchInterval: (query) =>
      !!query.state.data &&
      query.state.data.items?.some((t) =>
        ['awaiting_start', 'in_progress'].includes(t.status)
      )
        ? 5000
        : false,
    placeholderData: keepPreviousData,
  })
}
