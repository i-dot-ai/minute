'use client'

import { DiscardConfirmDialog } from '@/components/audio/discard-dialog'
import {
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
  listMinuteVersionsMinutesMinuteIdVersionsGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import Link from 'next/link'

const GENERATING_STATUSES = ['awaiting_start', 'in_progress']

function stepLabel(status: string | undefined): string {
  switch (status) {
    case 'completed':
      return 'Ready'
    case 'in_progress':
      return 'In progress'
    case 'failed':
      return 'Failed'
    default:
      return 'Waiting'
  }
}

export function GeneratingView({
  transcriptionId,
}: {
  transcriptionId: string
}) {
  // Phase 1: transcription
  const { data: transcription, isLoading } = useQuery({
    ...getTranscriptionTranscriptionsTranscriptionIdGetOptions({
      path: { transcription_id: transcriptionId },
    }),
    refetchInterval: (query) =>
      query.state.data?.status &&
        GENERATING_STATUSES.includes(query.state.data.status)
        ? 2000
        : false,
  })

  const transcriptionStatus = transcription?.status
  const transcriptionDone = transcriptionStatus === 'completed'

  // The minute (summary) is created up front, so we can read its id straight away.
  const { data: minutes = [] } = useQuery({
    ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions({
      path: { transcription_id: transcriptionId },
    }),
  })
  const minuteId = minutes[0]?.id

  // Phase 2: summary generation — only starts once transcription is done.
  const { data: minuteVersions = [] } = useQuery({
    ...listMinuteVersionsMinutesMinuteIdVersionsGetOptions({
      path: { minute_id: minuteId! },
    }),
    enabled: !!minuteId && transcriptionDone,
    refetchInterval: (query) =>
      query.state.data?.[0]?.status &&
        GENERATING_STATUSES.includes(query.state.data[0].status)
        ? 2000
        : false,
  })
  const summaryStatus = minuteVersions[0]?.status

  if (isLoading) {
    return (
      <div className="flex items-center gap-2">
        <Loader2 className="animate-spin" />
        <p className="govuk-body govuk-!-margin-bottom-0">Loading...</p>
      </div>
    )
  }

  if (!transcription) {
    return <p className="govuk-body">Transcription not found.</p>
  }

  const title =
    transcriptionStatus === 'failed'
      ? 'Transcription failed'
      : summaryStatus === 'failed'
        ? 'Summary failed'
        : !transcriptionDone
          ? 'Transcribing'
          : summaryStatus === 'completed'
            ? 'Transcription and summary ready'
            : 'Generating summary'

  return (
    <div>
      <h2 className="govuk-heading-m govuk-!-margin-bottom-2">{title}</h2>
      <ul className="govuk-list">
        <li>Transcribing — {stepLabel(transcriptionStatus)}</li>
        {transcriptionDone && (
          <li>
            Generating summary —{' '}
            {stepLabel(transcriptionDone ? summaryStatus : undefined)}
          </li>
        )}
      </ul>

      <div className="govuk-button-group">
        {transcriptionDone && (
          <Link
            href={`/transcriptions/${transcriptionId}`}
            className="govuk-button"
          >
            View summary
          </Link>
        )}
        {(transcriptionStatus === 'failed' || summaryStatus === 'failed') && (
          <Link
            href={`/transcriptions/${transcriptionId}`}
            className="govuk-button"
          >
            View details
          </Link>
        )}
        <a
          href="/"
          className="govuk-button govuk-button--secondary"
        >
          Record another meeting
        </a>
        <button
          type="button"
          className="govuk-link link--warning ml-auto"
        >
          Discard recording
        </button>
      </div>

    </div>
  )
}
