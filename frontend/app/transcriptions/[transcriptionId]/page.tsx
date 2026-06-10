'use client'
import { GovukTranscriptionTabs } from '@/app/transcriptions/[transcriptionId]/GovukTranscriptionTabs'
import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
import { DownloadButton } from '@/components/download-button'
import {
  getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions,
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

export default function TranscriptionPage({
  params: { transcriptionId },
}: {
  params: { transcriptionId: string }
}) {
  const { data: transcription, isLoading } = useQuery({
    ...getTranscriptionTranscriptionsTranscriptionIdGetOptions({
      path: { transcription_id: transcriptionId },
    }),
    refetchInterval: (query) =>
      query.state.data?.status &&
        ['awaiting_start', 'in_progress'].includes(query.state.data.status)
        ? 2000
        : false,
  })

  const minutesEnabled =
    !!transcription?.status &&
    !['awaiting_start', 'in_progress', 'failed'].includes(transcription.status)

  const { data: minutes = [] } = useQuery({
    ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions({
      path: { transcription_id: transcriptionId },
    }),
    enabled: minutesEnabled,
  })

  const [selectedMinute, setSelectedMinute] = useState(0)

  useEffect(() => {
    setSelectedMinute(0)
  }, [minutes])

  if (isLoading) {
    return (
      <p className="govuk-body">Loading...</p>
    )
  }

  if (!transcription) {
    return (
      <>
        <p className="govuk-body">404 - Transcription not found</p>
        <p className="govuk-body">The transcription you are looking for does not exist.</p>
      </>
    )
  }

  const date = new Date(transcription.created_datetime).toLocaleString('en-GB', {
    year: 'numeric', month: 'long', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })

  if (
    transcription.status &&
    ['awaiting_start', 'in_progress'].includes(transcription.status)
  ) {
    return (
      <div className="govuk-grid-row govuk-!-margin-bottom-2">
        <div className="govuk-grid-column-two-thirds">
          <h1>
            Generating transcript
          </h1>
          <p className="govuk-body">{date}</p>
          <p className="govuk-body">The transcription is being processed. Return later to view the transcript.</p>
          <AudioPlayer transcriptionId={transcription.id} />
        </div>
        <div className="govuk-grid-column-one-third">
          <div className="govuk-button-group">
            <a href={`/transcriptions/${transcription.id}/delete`} role="button" className="govuk-button govuk-button--warning">
              Delete
            </a>
          </div>
        </div>
      </div>
    )
  }

  if (transcription.status == 'failed') {
    return (
      <div className="govuk-grid-row govuk-!-margin-bottom-2">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl govuk-!-margin-bottom-2">
            No title
          </h1>
          <p className="govuk-body">{date}</p>
          <p className="govuk-body">The transcription failed to process. Please try again.</p>
          <div className="govuk-button-group">
            <a
              href={`/transcriptions/${transcription.id}/delete`}
              role="button"
              data-module="govuk-button"
              className="govuk-button govuk-button--warning"
            >
              Delete
            </a>
          </div>
        </div>
      </div>
    )
  }
  return (
    <>
      <div className="govuk-grid-row govuk-!-margin-bottom-2">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl govuk-!-margin-bottom-2">
            {transcription.title}
          </h1>
          <p className="govuk-body">{date}</p>
          <div className="govuk-button-group">
            <a
              data-module="govuk-button"
              href={`/transcriptions/${transcription.id}/rename`}
              className="govuk-button govuk-button--secondary"
            >
              Rename
            </a>
            <a
              href={`/transcriptions/${transcription.id}/delete`}
              className="govuk-link link--warning"
            >
              Delete transcription
            </a>
          </div>
        </div>
      </div >
      <div className="govuk-!-margin-bottom-4">
        {minutes.length > 0 && (
          <>
            <label className="govuk-label" htmlFor="summary-history">
              Choose a summary
            </label>
            <select
              className="govuk-select"
              id="summary-history"
              name="summary-history"
              onChange={(e) => setSelectedMinute(Number(e.target.value))}
              value={selectedMinute}
            >
              {minutes.map((minute, index) => {
                const minuteDate = new Date(minute.updated_datetime).toLocaleDateString('en-GB', {
                  day: 'numeric',
                  month: 'numeric',
                  year: 'numeric',
                  hour: 'numeric',
                  minute: 'numeric',
                })
                return (
                  <option value={`${index}`} key={minute.id}>
                    {minute.template_name} - {minuteDate}
                  </option>
                )
              })}
            </select>
            <NewMinuteDialog
              transcriptionId={transcription.id!}
              agenda={minutes[selectedMinute]?.agenda ?? undefined}
            />
          </>
        )}
      </div>
      <GovukTranscriptionTabs
        transcription={transcription}
        minutes={minutes}
        selectedMinute={selectedMinute}
      />
    </>
  )
}

const AudioPlayer = ({ transcriptionId }: { transcriptionId: string }) => {
  const { data: recordings } = useQuery({
    ...getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions(
      { path: { transcription_id: transcriptionId } }
    ),
  })
  if (!recordings || recordings.length == 0) {
    return null
  }
  return (
    <div className="mb-2 flex w-full max-w-3xl flex-col gap-2 rounded border bg-white p-2">
      <audio controls src={recordings[0].url} className="w-full" />
      <div className="flex justify-end">
        <DownloadButton recordings={recordings} />
      </div>
    </div>
  )
}
