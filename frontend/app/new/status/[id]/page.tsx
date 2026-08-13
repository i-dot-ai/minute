'use client'

import {
  getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions,
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
  listMinuteVersionsMinutesMinuteIdVersionsGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { DownloadButton } from '@/components/download-button'
import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
import { RetryTranscriptionDialog } from '@/components/audio/retry-transcription-dialog'
import { DeleteTranscriptionButton } from '@/components/recent-meetings/delete-transcription-button'
import { useQuery } from '@tanstack/react-query'
import { Loader2, Check, RefreshCw, X } from 'lucide-react'
import Link from 'next/link'
import { use, useEffect, useRef, useState } from 'react'
import { LoadingBar } from '@/components/ui/loading-bar'

const GENERATING_STATUSES = ['awaiting_start', 'in_progress']

// Processing normally takes 5-12 minutes per hour of audio; flag as stalled
// at 18 minutes per hour (0.3 min per audio minute), with a floor for short
// clips and a flat fallback when the audio duration is unknown.
const STALL_MINUTES_PER_AUDIO_MINUTE = 0.3
const STALL_FLOOR_MS = 5 * 60 * 1000
const STALL_FALLBACK_MS = 15 * 60 * 1000

const getStallLimitMs = (durationSec: number | null) =>
  durationSec
    ? Math.max(
      STALL_FLOOR_MS,
      (durationSec / 60) * STALL_MINUTES_PER_AUDIO_MINUTE * 60 * 1000
    )
    : STALL_FALLBACK_MS

export default function RecordStatusPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)
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

  const minutesQuery = useQuery({
    ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions(
      {
        path: { transcription_id: id },
      }
    ),
  })
  const minutes = minutesQuery.data ?? []
  const minuteId = minutes[0]?.id

  const minuteVersionsQuery = useQuery({
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
  const summaryStatus = minuteVersionsQuery.data?.[0]?.status

  // Once transcription completes, the summary state is unknown until the
  // minutes list and the (just-enabled) versions query have returned; keep
  // showing the processing state to avoid a flash of "Ready".
  const summaryStatusPending =
    transcriptionDone &&
    (minutesQuery.isLoading || (!!minuteId && minuteVersionsQuery.isLoading))

  const { data: recordings = [] } = useQuery({
    ...getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions(
      {
        path: { transcription_id: id },
      }
    ),
  })
  const recordingUrl = recordings[0]?.url

  const [audioDurationSec, setAudioDurationSec] = useState<number | null>(null)
  const durationSec =
    audioDurationSec ??
    transcription?.dialogue_entries?.at(-1)?.end_time ??
    null

  const isProcessing =
    transcriptionStatus === 'in_progress' ||
    transcriptionStatus === 'awaiting_start' ||
    summaryStatus === 'in_progress' ||
    summaryStatus === 'awaiting_start' ||
    summaryStatusPending
  const isFailed =
    transcriptionStatus === 'failed' || summaryStatus === 'failed'

  const stallSince = transcriptionDone
    ? minuteVersionsQuery.data?.[0]?.created_datetime
    : transcription?.created_datetime
  const isStalled =
    isProcessing &&
    !!stallSince &&
    Date.now() - new Date(stallSince).getTime() > getStallLimitMs(durationSec)

  const getEstimatedTimeToComplete = (durationSec: number | null) => {
    if (!durationSec) return null
    const minutes = durationSec / 60
    return Math.round(minutes)
  }

  const estimatedTimeToComplete = getEstimatedTimeToComplete(durationSec)

  // Land keyboard/screen-reader focus on the page heading after the client-side
  // navigation from the recorder, which otherwise leaves focus on <body>.
  const headingRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    headingRef.current?.focus()
  }, [])

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
                  <audio
                    controls
                    src={recordingUrl}
                    className="w-full"
                    onLoadedMetadata={(e) => {
                      const d = e.currentTarget.duration
                      if (Number.isFinite(d)) setAudioDurationSec(d)
                    }}
                  />
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
                <div className="govuk-!-margin-bottom-6 inline-flex items-center gap-2">
                  <RefreshCw className="size-4 animate-spin text-(--govuk-text-colour)" />
                  <h2 className="govuk-heading-m govuk-!-margin-bottom-0">
                    {transcriptionDone ? 'Generating summary' : 'Transcribing'}
                  </h2>
                </div>

                {isStalled ? (
                  <div className="govuk-warning-text">
                    <span
                      className="govuk-warning-text__icon"
                      aria-hidden="true"
                    >
                      !
                    </span>
                    <strong className="govuk-warning-text__text">
                      <span className="govuk-visually-hidden">Warning</span>
                      Taking longer than usual. Leave this page if needed, it
                      will continue in the background.
                    </strong>
                  </div>
                ) : (
                  <p className="govuk-body">
                    Estimated time to complete:{' '}
                    <strong>{estimatedTimeToComplete} minutes</strong>
                  </p>
                )}
                <div className="govuk-!-margin-bottom-7 govuk-!-margin-top-6">
                  <LoadingBar />
                </div>
              </>
            ) : isFailed ? (
              <>
                <div className="govuk-!-margin-bottom-4 inline-flex items-center gap-2">
                  <X className="size-4 text-(--govuk-error-colour)" />
                  <h2 className="govuk-heading-m govuk-!-margin-bottom-0">
                    Failed to process
                  </h2>
                </div>
                <p className="govuk-body">
                  The recording is safe, only the transcription failed.
                </p>

                <p className="govuk-body">
                  Please try again. If it continues to fail,{' '}
                  <Link href="/support" className="govuk-link">
                    contact support
                  </Link>
                  .
                </p>
              </>
            ) : (
              <>
                <div className="inline-flex items-center gap-2">
                  <Check className="size-4 text-[#0f7a52]" />
                  <h2 className="govuk-heading-m govuk-!-margin-bottom-0">
                    Ready
                  </h2>
                </div>
                <p className="govuk-body govuk-!-margin-top-3">
                  View and edit the transcription and summary at any time.
                </p>
              </>
            )}
            <div className="govuk-button-group govuk-!-margin-top-6">
              {!isProcessing &&
                (isFailed ? (
                  <>
                    {transcriptionDone ? (
                      <NewMinuteDialog
                        transcriptionId={id}
                        agenda={minutes[0]?.agenda ?? undefined}
                        buttonLabel="Try again"
                        buttonClassName="govuk-button"
                      />
                    ) : (
                      recordings[0] && (
                        <RetryTranscriptionDialog
                          recordingId={recordings[0].id}
                          agenda={minutes[0]?.agenda ?? undefined}
                          title={transcription.title ?? undefined}
                        />
                      )
                    )}
                    <Link
                      href={`/transcriptions/${id}`}
                      className="govuk-button govuk-button--secondary"
                    >
                      View details
                    </Link>
                  </>
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
