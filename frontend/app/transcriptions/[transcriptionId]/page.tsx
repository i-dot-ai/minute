'use client'
import { GovukTranscriptionTabs } from '@/app/transcriptions/[transcriptionId]/GovukTranscriptionTabs'
import { DownloadButton } from '@/components/download-button'
import {
  getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions,
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { Loader2, PencilIcon } from 'lucide-react'

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

  if (isLoading) {
    return (
      <div className="flex items-center gap-2">
        <Loader2 className="animate-spin" />
        <p className="govuk-body govuk-!-margin-bottom-0">Loading...</p>
      </div>
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
          <h1 className="govuk-heading-xl govuk-!-margin-bottom-2">
            Generating transcript
          </h1>
          <p className="govuk-body">{date}</p>
          <p className="govuk-body">The transcription is being processed. Return later to view the transcript.</p>
          <h2 className="govuk-heading-m">Audio</h2>
          <AudioPlayer transcriptionId={transcription.id} />
        </div>
        <div className="govuk-grid-column-one-third">
          <div className="govuk-button-group">
            <a href={`/transcriptions/${transcription.id}/delete`} className="govuk-link link--warning">
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
        </div>
        <div className="govuk-grid-column-one-third">
          <a
            href={`/transcriptions/${transcription.id}/delete`}
            className="govuk-link link--warning float-right"
          >
            Delete
          </a>
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
        </div>
        <div className="govuk-grid-column-one-third">
          <div className="govuk-button-group transcription-page__actions">
            <a
              data-module="govuk-button"
              href={`/transcriptions/${transcription.id}/rename`}
              className="govuk-button govuk-button--secondary"
            >
              <PencilIcon /> Rename
            </a>
            <a
              href={`/transcriptions/${transcription.id}/delete`}
              className="govuk-link link--warning"
            >
              Delete
            </a>
          </div>
        </div>
      </div >
      <GovukTranscriptionTabs transcription={transcription} minutes={minutes} />
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
    <div>
      <audio controls src={recordings[0].url} className="w-full" />
      <div className="govuk-!-margin-top-2">
        <DownloadButton recordings={recordings} />
      </div>
    </div>
  )
}
