'use client'
import ChatTab from '@/app/transcriptions/[transcriptionId]/ChatTab/ChatTab'
import { MinuteTab } from '@/app/transcriptions/[transcriptionId]/MinuteTab/MinuteTab'
import { TranscriptionTab } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/TranscriptionTab'
import { DownloadButton } from '@/components/download-button'
import { AudioWav } from '@/components/icons/AudioWav'
import { TranscriptionTitleEditor } from '@/components/transcription-title-editor'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions,
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { FeatureFlags } from '@/lib/feature-flags'
import { useQuery } from '@tanstack/react-query'
import { Clock, Frown, LoaderCircle, SearchX } from 'lucide-react'
import Link from 'next/link'
import { useFeatureFlagEnabled } from 'posthog-js/react'

export default function TranscriptionPage({
  params: { transcriptionId },
}: {
  params: { transcriptionId: string }
}) {
  const isChatEnabled = useFeatureFlagEnabled(FeatureFlags.ChatEnabled)

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
          <p className="govuk-caption-l govuk-!-margin-top-0">Summary</p>
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
              role="button"
              data-module="govuk-button"
              className="govuk-button govuk-button--warning"
            >
              Delete
            </a>
          </div>

          <p className="govuk-body govuk-!-font-weight-bold govuk-!-margin-bottom-1">
            <Link href={`/transcriptions/${transcription.id}/transcript`} className="govuk-link">
              View transcript
            </Link>
          </p>
          <p className="govuk-body">Read, edit and download the full transcript.</p>
        </div>
      </div >
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-full govuk-!-margin-bottom-6">
          <div style={{ borderBottom: '1px solid #b1b4b6' }} />
        </div>
      </div>
      <MinuteTab transcription={transcription} />
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
