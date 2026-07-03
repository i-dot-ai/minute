'use client'

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

export default function RecordStatusPage({
  params: { id },
}: {
  params: { id: string }
}) {
  const { data: transcription, isLoading } = useQuery({
    ...getTranscriptionTranscriptionsTranscriptionIdGetOptions({
      path: { transcription_id: id },
    }),
    refetchInterval: (query) =>
      query.state.data?.status &&
      GENERATING_STATUSES.includes(query.state.data.status)
        ? 2000
        : false,
  })

  const transcriptionStatus = transcription?.status
  const transcriptionDone = transcriptionStatus === 'completed'

  const { data: minutes = [] } = useQuery({
    ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions(
      {
        path: { transcription_id: id },
      }
    ),
  })
  const minuteId = minutes[0]?.id

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
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-full">
          <h1 className="govuk-heading-l">Record a meeting</h1>
          {isLoading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="animate-spin" />
              <p className="govuk-body govuk-!-margin-bottom-0">Loading...</p>
            </div>
          ) : !transcription ? (
            <p className="govuk-body">Transcription not found.</p>
          ) : (
            <div>
              <h2 className="govuk-heading-m govuk-!-margin-bottom-2">
                {title}
              </h2>
              <ul className="govuk-list">
                <li>Transcribing — {stepLabel(transcriptionStatus)}</li>
                {transcriptionDone && (
                  <li>Generating summary — {stepLabel(summaryStatus)}</li>
                )}
              </ul>

              <div className="govuk-button-group">
                {transcriptionDone && (
                  <Link href={`/transcriptions/${id}`} className="govuk-button">
                    View summary
                  </Link>
                )}
                {(transcriptionStatus === 'failed' ||
                  summaryStatus === 'failed') && (
                  <Link href={`/transcriptions/${id}`} className="govuk-button">
                    View details
                  </Link>
                )}
                <Link href="/" className="govuk-button govuk-button--secondary">
                  Record another meeting
                </Link>
                <button
                  type="button"
                  className="govuk-link link--warning ml-auto"
                >
                  Discard recording
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
