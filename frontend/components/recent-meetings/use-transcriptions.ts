'use client'

import { TranscriptionListFilter } from '@/lib/client'
import {
  listTranscriptionsTranscriptionsGetOptions,
  searchTranscriptionsTranscriptionsSearchGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { keepPreviousData, useQuery } from '@tanstack/react-query'

export function useTranscriptions({
  page,
  pageSize,
  filterBy,
  search,
}: {
  page: number
  pageSize: number
  filterBy?: TranscriptionListFilter
  search?: string
}) {
  const query = { page, page_size: pageSize, filter_by: filterBy }
  const options = search
    ? // Search results are a superset of list items, so the list table renders them unchanged.
      (searchTranscriptionsTranscriptionsSearchGetOptions({
        query: { ...query, search },
      }) as unknown as ReturnType<
        typeof listTranscriptionsTranscriptionsGetOptions
      >)
    : listTranscriptionsTranscriptionsGetOptions({ query })

  return useQuery({
    ...options,
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
