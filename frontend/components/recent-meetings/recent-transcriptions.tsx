'use client'

import { TranscriptionsList } from '@/components/recent-meetings/transcriptions-list'
import { useTranscriptions } from '@/components/recent-meetings/use-transcriptions'

const RECENT_COUNT = 3

export function RecentTranscriptions() {
  const { data, isLoading, error } = useTranscriptions({
    page: 1,
    pageSize: RECENT_COUNT,
  })
  const transcriptions = data?.items ?? []

  if (isLoading) {
    return <p className="govuk-body">Loading transcriptions...</p>
  }

  if (error) {
    return <p className="govuk-body">Error loading transcriptions</p>
  }

  if (transcriptions.length === 0) {
    return <p className="govuk-body">No transcriptions found. Your most recent transcriptions will appear here.</p>
  }

  return <TranscriptionsList transcriptions={transcriptions} />
}
