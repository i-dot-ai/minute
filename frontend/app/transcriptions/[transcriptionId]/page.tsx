'use client'
import { GovukTranscriptionTabs } from '@/app/transcriptions/[transcriptionId]/GovukTranscriptionTabs'
import { DownloadButton } from '@/components/download-button'
import { DeleteTranscriptionButton } from '@/components/recent-meetings/delete-transcription-button'
import { RenameTranscriptionInline } from '@/components/recent-meetings/rename-transcription'
import {
  getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions,
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { AudioWav } from '@/components/icons/AudioWav'
import Link from 'next/link'
import { useState } from 'react'

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
  const [isEditing, setIsEditing] = useState(false)

  const minutesEnabled =
    !!transcription?.status &&
    !['awaiting_start', 'in_progress', 'failed'].includes(transcription.status)

  const { data: minutes = [] } = useQuery({
    ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions(
      {
        path: { transcription_id: transcriptionId },
      }
    ),
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
        <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
          <ol className="govuk-breadcrumbs__list">
            <li className="govuk-breadcrumbs__list-item">
              <Link href="/transcriptions" className="govuk-breadcrumbs__link">
                Back to transcriptions
              </Link>
            </li>
          </ol>
        </nav>
        <h1 className="govuk-heading-l govuk-!-margin-bottom-2">404 - Transcription not found</h1>
        <p className="govuk-body">
          The transcription you are looking for does not exist.
        </p>
        <div className="govuk-button-group">
          <Link href="/transcriptions" className="govuk-button">
            Back to transcriptions
          </Link>
        </div>
      </>
    )
  }

  const date = new Date(transcription.created_datetime).toLocaleString(
    'en-GB',
    {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }
  )

  if (
    transcription.status &&
    ['awaiting_start', 'in_progress'].includes(transcription.status)
  ) {
    return (
      <div className="govuk-grid-row govuk-!-margin-bottom-2">
        <div className="govuk-grid-column-three-quarters">
          <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
            <ol className="govuk-breadcrumbs__list">
              <li className="govuk-breadcrumbs__list-item">
                <Link href="/transcriptions" className="govuk-breadcrumbs__link">
                  Back to transcriptions
                </Link>
              </li>
            </ol>
          </nav>
          <h1 className="govuk-heading-l govuk-!-margin-bottom-2">
            Generating transcript
          </h1>
          <p className="govuk-body">{date}</p>
          <p className="govuk-body">
            The transcription is being processed. Return later to view the
            transcript.
          </p>
          <div className="flex w-full justify-center">
            <AudioWav />
          </div>
          <h2 className="govuk-heading-m">Audio</h2>
          <AudioPlayer transcriptionId={transcription.id} />
        </div>
        <div className="govuk-grid-column-one-quarter">
          <div className="govuk-button-group">
            <DeleteTranscriptionButton transcription={transcription} />
          </div>
        </div>
      </div>
    )
  }

  if (transcription.status == 'failed') {
    return (
      <>
        <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
          <ol className="govuk-breadcrumbs__list">
            <li className="govuk-breadcrumbs__list-item">
              <Link href="/transcriptions" className="govuk-breadcrumbs__link">
                Back to transcriptions
              </Link>
            </li>
          </ol>
        </nav>
        <div className="govuk-grid-row govuk-!-margin-bottom-2">
          <div className="govuk-grid-column-three-quarters">
            <RenameTranscriptionInline
              transcription={transcription}
              headingLevel="h1"
              headingClassName="govuk-heading-xl govuk-!-margin-bottom-2"
            />
            <p className="govuk-body">{date}</p>
            <p className="govuk-body">
              The transcription failed to process. Please try again.
            </p>
          </div>
          <div className="govuk-grid-column-one-quarter">
            <div className="govuk-button-group transcription-page__actions float-right">
              <DeleteTranscriptionButton transcription={transcription} />
            </div>
          </div>
        </div>
        <div className="govuk-grid-row govuk-!-margin-bottom-2">
          <div className="govuk-grid-column-two-thirds">
            <h2 className="govuk-heading-m">Audio:</h2>
            <AudioPlayer transcriptionId={transcription.id} />
          </div>
        </div>
      </>
    )
  }
  return (
    <>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-one-third">
          <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
            <ol className="govuk-breadcrumbs__list">
              <li className="govuk-breadcrumbs__list-item">
                <Link href="/transcriptions" className="govuk-breadcrumbs__link">
                  Back to transcriptions
                </Link>
              </li>
            </ol>
          </nav>
        </div>
        <div className="govuk-grid-column-two-thirds">
          <div className="govuk-button-group transcription-page__actions">
            <button type="button" className="govuk-button govuk-button--secondary" onClick={() => setIsEditing(true)}>
              Edit
            </button>
            <button type="button" className="govuk-button govuk-button--secondary" disabled={isEditing}>
              Download
            </button>
            <button type="button" className="govuk-button govuk-button--secondary" disabled={isEditing}>
              Copy
            </button>
            <DeleteTranscriptionButton transcription={transcription} disabled={isEditing} />
          </div>
        </div>
      </div>
      <div className="govuk-grid-row govuk-!-margin-bottom-2">
        <div className="govuk-grid-column-full">
          <h1 className="govuk-heading-l govuk-!-margin-bottom-2">{transcription.title}</h1>
          <p className="govuk-body">{date}</p>
        </div>
      </div>
      <GovukTranscriptionTabs transcription={transcription} minutes={minutes} isEditing={isEditing} setIsEditing={setIsEditing} />
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
      <div className="govuk-button-group govuk-!-margin-top-2">
        <DownloadButton recordings={recordings} />
      </div>
    </div>
  )
}
