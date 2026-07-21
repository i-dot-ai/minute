'use client'

import {
  getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions,
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
  listMinuteVersionsMinutesMinuteIdVersionsGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { DownloadButton } from '@/components/download-button'
import { DeleteTranscriptionButton } from '@/components/recent-meetings/delete-transcription-button'
import { useQuery } from '@tanstack/react-query'
import { Loader2, Check, RefreshCw, X } from 'lucide-react'
import Link from 'next/link'
import { useEffect, useRef } from 'react'
import { LoadingBar } from '@/components/ui/loading-bar'

const GENERATING_STATUSES = ['awaiting_start', 'in_progress']

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

  const { data: recordings = [] } = useQuery({
    ...getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions(
      {
        path: { transcription_id: id },
      }
    ),
  })
  const recordingUrl = recordings[0]?.url
  const isProcessing =
    transcriptionStatus === 'in_progress' ||
    transcriptionStatus === 'awaiting_start' ||
    summaryStatus === 'in_progress' ||
    summaryStatus === 'awaiting_start'
  const isFailed =
    transcriptionStatus === 'failed' || summaryStatus === 'failed'

  // Land keyboard/screen-reader focus on the page heading after the client-side
  // navigation from the recorder, which otherwise leaves focus on <body>.
  const headingRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  const lengthSeconds = transcription?.dialogue_entries?.at(-1)?.end_time
  function formatLength(seconds: number): string {
    const totalMinutes = Math.round(seconds / 60)
    if (totalMinutes < 1) {
      return '1 min'
    }
    if (totalMinutes < 60) {
      return `${totalMinutes} ${totalMinutes === 1 ? 'min' : 'mins'}`
    }
    const hours = Math.floor(totalMinutes / 60)
    const minutes = totalMinutes % 60
    const hoursLabel = `${hours} ${hours === 1 ? 'hr' : 'hrs'}`
    if (minutes === 0) return hoursLabel
    return `${hoursLabel} ${minutes} ${minutes === 1 ? 'min' : 'mins'}`
  }

  const meetingLength = lengthSeconds ? formatLength(lengthSeconds) : ''

  return (
    <div className="govuk-width-container govuk-!-padding-top-4">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-three-quarters">
          <h1 ref={headingRef} tabIndex={-1} className="govuk-heading-l">
            Record a meeting
          </h1>
        </div>
        <div className="govuk-grid-column-one-quarter">
          <div className="govuk-button-group flex justify-end">
            {transcription && (
              <DeleteTranscriptionButton transcription={transcription} />
            )}
          </div>
        </div>
      </div>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-full">
          {transcription && (
            <p className="govuk-body">
              You can leave this page and view the transcription and summary
              when it is ready.
            </p>
          )}
        </div>
      </div>
      {isLoading ? (
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-full">
            <div className="flex items-center gap-2">
              <Loader2 className="animate-spin" />
              <p className="govuk-body govuk-!-margin-bottom-0">Loading...</p>
            </div>
          </div>
        </div>
      ) : !transcription ? (
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-full">
            <p className="govuk-body">Transcription not found.</p>
            <div className="govuk-button-group govuk-!-margin-top-5">
              <Link href="/transcriptions" className="govuk-button">
                View transcriptions
              </Link>
            </div>
          </div>
        </div>
      ) : (
        <>
          {recordingUrl && (
            <>
              <div className="govuk-grid-row govuk-!-margin-top-5">
                <div className="govuk-grid-column-one-half">
                  <audio controls src={recordingUrl} className="w-full" />
                </div>
                <div className="govuk-grid-column-one-half">
                  <div className="govuk-button-group govuk-!-margin-bottom-0 govuk-!-margin-top-1">
                    <DownloadButton recordings={recordings} />
                    <Link
                      href="/"
                      className="govuk-button govuk-button--secondary"
                    >
                      Record another meeting
                    </Link>
                  </div>
                </div>
              </div>
            </>
          )}
          <div className="govuk-!-padding-5 govuk-!-padding-top-8 govuk-!-margin-top-5 bg-(--govuk-surface-background-colour)">
            {isProcessing ? (
              <>
                <div className="inline-flex items-center gap-2">
                  <RefreshCw className="size-4 animate-spin text-(--govuk-text-colour)" />
                  <h2 className="govuk-heading-m govuk-!-margin-bottom-0">
                    {transcriptionDone ? 'Generating summary' : 'Transcribing'}
                  </h2>
                </div>
                <div className="govuk-!-margin-bottom-7 govuk-!-margin-top-6">
                  <LoadingBar />
                </div>
              </>
            ) : isFailed ? (
              <div className="inline-flex items-center gap-2">
                <X className="size-4 text-(--govuk-error-colour)" />
                <h2 className="govuk-heading-m govuk-!-margin-bottom-0">
                  Failed to process
                </h2>
              </div>
            ) : (
              <>
                <div className="inline-flex items-center gap-2">
                  <Check className="size-4 text-[#0f7a52]" />
                  <h2 className="govuk-heading-m govuk-!-margin-bottom-0">
                    Ready
                  </h2>
                </div>
                <p className="govuk-body govuk-!-margin-top-3">
                  {/* {meetingLength} -{' '}
                  {new Date(transcription.created_datetime).toLocaleString(
                    'en-GB',
                    {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    }
                  )} */}
                  View and edit the transcription and summary at any time.
                </p>
              </>
            )}
            <div className="govuk-button-group govuk-!-margin-top-6">
              {!isProcessing &&
                (isFailed ? (
                  <Link href={`/transcriptions/${id}`} className="govuk-button">
                    View details
                  </Link>
                ) : (
                  <Link href={`/transcriptions/${id}`} className="govuk-button">
                    View transcription
                  </Link>
                ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
