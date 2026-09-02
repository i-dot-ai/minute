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
import { Loader2, Check, X } from 'lucide-react'
import Link from 'next/link'
import { use, useEffect, useRef, useState } from 'react'
import { ProcessingCard } from '@/components/processing-card'
import { useNow } from '@/hooks/use-now'
import {
  getIsStalled,
  getRemainingMinutes,
  getSummaryEstimateMinutes,
  getTotalEstimateMinutes,
  ProcessingPhase,
} from '@/lib/processing-estimate'
import { readRecordingDurationSec } from '@/lib/recording-duration'

const GENERATING_STATUSES = ['awaiting_start', 'in_progress']

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
  // The recorder stashes the measured length keyed by this id, so the estimate
  // can show while transcribing — before the transcript or audio URL exists.
  const [storedDurationSec, setStoredDurationSec] = useState<number | null>(
    null
  )
  useEffect(() => {
    setStoredDurationSec(readRecordingDurationSec(id))
  }, [id])
  const durationSec =
    audioDurationSec ??
    transcription?.dialogue_entries?.at(-1)?.end_time ??
    storedDurationSec ??
    null

  const isProcessing =
    transcriptionStatus === 'in_progress' ||
    transcriptionStatus === 'awaiting_start' ||
    summaryStatus === 'in_progress' ||
    summaryStatus === 'awaiting_start' ||
    summaryStatusPending
  const isFailed =
    transcriptionStatus === 'failed' || summaryStatus === 'failed'

  const now = useNow({ enabled: isProcessing })

  // The summary phase re-anchors on the version being generated, so both the
  // countdown and the stall check restart when transcription hands over.
  const phase: ProcessingPhase = transcriptionDone ? 'summary' : 'transcription'
  const phaseStartedAt = transcriptionDone
    ? minuteVersionsQuery.data?.[0]?.created_datetime
    : transcription?.created_datetime

  const isStalled =
    isProcessing &&
    getIsStalled({ startedAt: phaseStartedAt, durationSec, phase, now })

  // While transcribing, the countdown covers the whole job but is held back at
  // the summary estimate, so it never reaches zero with the summary still to
  // run. Once the summary starts it counts that estimate down on its own.
  const summaryEstimateMinutes = getSummaryEstimateMinutes(durationSec)
  const remainingMinutes = getRemainingMinutes({
    startedAt: phaseStartedAt,
    estimateMinutes: transcriptionDone
      ? summaryEstimateMinutes
      : getTotalEstimateMinutes(durationSec),
    minimumMinutes: transcriptionDone ? 0 : summaryEstimateMinutes,
    now,
  })

  // Land keyboard/screen-reader focus on the page heading after the client-side
  // navigation from the recorder, which otherwise leaves focus on <body>.
  const headingRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  return (
    <div className="govuk-width-container govuk-main-wrapper">
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
          {isProcessing ? (
            <ProcessingCard
              className="govuk-!-margin-top-5"
              heading={
                transcriptionDone ? 'Generating summary' : 'Transcribing'
              }
              remainingMinutes={remainingMinutes}
              isStalled={isStalled}
            />
          ) : (
            <div className="govuk-!-padding-5 govuk-!-padding-top-8 govuk-!-margin-top-5 bg-(--govuk-surface-background-colour)">
              {isFailed ? (
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
                {isFailed ? (
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
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
