'use client'

import {
  getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions,
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
  listMinuteVersionsMinutesMinuteIdVersionsGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { DownloadButton } from '@/components/download-button'
import { useQuery } from '@tanstack/react-query'
import { Loader2, PlusIcon } from 'lucide-react'
import Link from 'next/link'
import { LoadingBar } from '@/components/ui/loading-bar'

const GENERATING_STATUSES = ['awaiting_start', 'in_progress']

function StatusTag({ status }: { status: string | undefined }) {
  const { colour, label } = (() => {
    switch (status) {
      case 'completed':
        return { colour: 'green', label: 'Ready' }
      case 'in_progress':
        return { colour: 'blue', label: 'Processing' }
      case 'failed':
        return { colour: 'red', label: 'Failed' }
      default:
        return { colour: 'grey', label: 'Waiting' }
    }
  })()

  return <strong className={`govuk-tag govuk-tag--${colour}`}>{label}</strong>
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

  const { data: recordings = [] } = useQuery({
    ...getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions(
      {
        path: { transcription_id: id },
      }
    ),
  })
  const recordingUrl = recordings[0]?.url
  const isProcessing =
    transcriptionStatus === 'in_progress' || summaryStatus === 'in_progress'

  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-one-third">
          <h1 className="govuk-heading-l">New meeting</h1>
        </div>
        <div className="govuk-grid-column-two-thirds">
          <div className="govuk-button-group flex justify-end">
            <Link
              href="/"
              className="govuk-button govuk-button--secondary"
            >
              <PlusIcon className="size-4" />
              New meeting
            </Link>
            <DownloadButton recordings={recordings} />
            <button
              type="button"
              className="govuk-link link--warning"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-full">
          <p className="govuk-body">
            You can leave this page and view the transcription and summary when it is ready.
          </p>
        </div>
      </div>
      <div className="govuk-grid-row">
        {isLoading ? (
          <div className="flex items-center gap-2">
            <Loader2 className="animate-spin" />
            <p className="govuk-body govuk-!-margin-bottom-0">Loading...</p>
          </div>
        ) : !transcription ? (
          <p className="govuk-body">Transcription not found.</p>
        ) : (
          <div className="govuk-grid-column-full">
            {recordingUrl && (
              <>
                <audio
                  controls
                  src={recordingUrl}
                  className="govuk-!-margin-bottom-9 govuk-!-margin-top-5 w-full"
                />
              </>
            )}
            <h2 className="govuk-heading-m">
              Transcription {isProcessing ? 'processing' : 'ready'}
            </h2>
            {isProcessing && (
              <div className="govuk-!-margin-bottom-7 govuk-!-margin-top-6">
                <LoadingBar />
              </div>
            )}
            <ul className="govuk-list govuk-list--spaced">
              <li>
                Transcription <StatusTag status={transcriptionStatus} />
              </li>
              <li>
                Summary <StatusTag status={summaryStatus} />
              </li>
            </ul>
            <div className="govuk-button-group govuk-!-margin-top-9">
              {transcriptionDone && (
                <Link
                  href={`/transcriptions/${id}`}
                  className="govuk-button govuk-button--start"
                >
                  View transcription
                  <svg className="govuk-button__start-icon" xmlns="http://www.w3.org/2000/svg" width="17.5" height="19" viewBox="0 0 33 40" aria-hidden="true" focusable="false">
                    <path fill="currentColor" d="M0 0h13l20 20-20 20H0l20-20z" />
                  </svg>
                </Link>
              )}
              {(transcriptionStatus === 'failed' ||
                summaryStatus === 'failed') && (
                  <Link
                    href={`/transcriptions/${id}`}
                    className="govuk-button"
                  >
                    View details
                  </Link>
                )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
