'use client'
import { DownloadButton } from '@/components/download-button'
import { useRenameTranscription } from '@/components/recent-meetings/rename-transcription'
import {
  getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions,
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { RetryTranscriptionDialog } from '@/components/audio/retry-transcription-dialog'
import { useQuery } from '@tanstack/react-query'
import { Loader2, Pencil, Save } from 'lucide-react'
import { AudioWav } from '@/components/icons/AudioWav'
import Link from 'next/link'
import { useRouter, useParams } from 'next/navigation'
import { useEffect, useState } from 'react'

export default function TranscriptionPage() {
  const { transcriptionId } = useParams<{ transcriptionId: string }>()
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
  const router = useRouter()

  const [isRenaming, setIsRenaming] = useState(false)
  const [draftTitle, setDraftTitle] = useState('')
  const { save: saveTitle, isPending: isSavingTitle } = useRenameTranscription({
    id: transcriptionId,
    title: transcription?.title,
    status: transcription?.status ?? 'completed',
  })

  const minutesEnabled =
    !!transcription?.status &&
    !['awaiting_start', 'in_progress', 'failed'].includes(transcription.status)

  const { data: minutes = [], isSuccess: minutesLoaded } = useQuery({
    ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions(
      {
        path: { transcription_id: transcriptionId },
      }
    ),
    enabled: minutesEnabled,
  })

  const { data: recordings = [] } = useQuery({
    ...getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions(
      {
        path: { transcription_id: transcriptionId },
      }
    ),
    enabled: transcription?.status === 'failed',
  })

  useEffect(() => {
    if (minutesEnabled && minutesLoaded) {
      router.replace(
        minutes.length > 0
          ? `/transcriptions/${transcriptionId}/summary/${minutes[0].id}`
          : `/transcriptions/${transcriptionId}/transcript`
      )
    }
  }, [minutesEnabled, minutesLoaded, minutes, router, transcriptionId])

  if (isLoading) {
    return (
      <div className="govuk-!-padding-top-4 govuk-width-container govuk-width-container--with-secondary-nav">
        <div className="flex items-center gap-2">
          <Loader2 className="animate-spin" />
          <p className="govuk-body govuk-!-margin-bottom-0">Loading...</p>
        </div>
      </div>
    )
  }

  if (!transcription) {
    return (
      <div className="govuk-!-padding-top-4 govuk-width-container govuk-width-container--with-secondary-nav">
        <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
          <ol className="govuk-breadcrumbs__list">
            <li className="govuk-breadcrumbs__list-item">
              <Link href="/transcriptions" className="govuk-breadcrumbs__link">
                Back
              </Link>
            </li>
          </ol>
        </nav>
        <h1 className="govuk-heading-l govuk-!-margin-bottom-2">
          404 - Transcription not found
        </h1>
        <p className="govuk-body">
          The transcription you are looking for does not exist.
        </p>
        <div className="govuk-button-group">
          <Link href="/transcriptions" className="govuk-button">
            Back to transcriptions
          </Link>
        </div>
      </div>
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
      <div className="govuk-!-padding-top-4 govuk-width-container govuk-width-container--with-secondary-nav">
        <div className="govuk-grid-row govuk-!-margin-bottom-2">
          <div className="govuk-grid-column-three-quarters">
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
        </div>
      </div>
    )
  }

  if (transcription.status == 'failed') {
    return (
      <div>
        <div className="govuk-!-padding-top-4 border-b border-(--govuk-border-colour)">
          <div className="govuk-width-container govuk-width-container--with-secondary-nav">

            <div className="sm:flex sm:justify-between">
              <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
                <ol className="govuk-breadcrumbs__list">
                  <li className="govuk-breadcrumbs__list-item">
                    <Link
                      href="/transcriptions"
                      className="govuk-breadcrumbs__link"
                    >
                      Back
                    </Link>
                  </li>
                </ol>
              </nav>
              <div className="govuk-button-group transcription-page__actions govuk-!-margin-bottom-0 justify-end">
                <button
                  type="button"
                  className="govuk-button govuk-button--secondary"
                  disabled={isRenaming}
                  onClick={() => {
                    setDraftTitle(transcription.title ?? '')
                    setIsRenaming(true)
                  }}
                >
                  <Pencil className="size-4" /> Rename
                </button>
              </div>
            </div>
          </div>
        </div>
        <div className="govuk-width-container govuk-width-container--with-secondary-nav govuk-main-wrapper">
          <div className="govuk-grid-row govuk-!-margin-bottom-2">
            <div className="govuk-grid-column-two-thirds">
              {!isRenaming && (
                <h1 className="govuk-heading-l govuk-!-margin-bottom-2">
                  {transcription.title ?? 'No title'}
                </h1>
              )}
            </div>
            <div
              className={
                isRenaming
                  ? 'govuk-grid-column-full'
                  : 'govuk-grid-column-one-third'
              }
            >
            </div>
          </div>
          {isRenaming && (
            <form
              className="govuk-form-group"
              onSubmit={(e) => {
                e.preventDefault()
                saveTitle(draftTitle)
                setIsRenaming(false)
              }}
            >
              <h1 className="govuk-label-wrapper">
                <label
                  className="govuk-label govuk-label--m"
                  htmlFor="transcription-title"
                >
                  Transcription title
                </label>
              </h1>
              <input
                id="transcription-title"
                className="govuk-input"
                type="text"
                placeholder="Add title"
                value={draftTitle}
                onChange={(e) => setDraftTitle(e.target.value)}
              />
              <div className="govuk-button-group govuk-!-margin-top-2">
                <button
                  type="submit"
                  className="govuk-button"
                  disabled={isSavingTitle}
                >
                  <Save className="size-4" /> Save
                </button>
                <button
                  type="button"
                  className="govuk-button govuk-button--secondary"
                  onClick={() => setIsRenaming(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
          <div className="govuk-grid-row govuk-!-margin-bottom-2">
            <div className="govuk-grid-column-two-thirds">
              <p className="govuk-body">{date}</p>
              <div className="govuk-warning-text">
                <span className="govuk-warning-text__icon" aria-hidden="true">
                  !
                </span>
                <strong className="govuk-warning-text__text">
                  <span className="govuk-visually-hidden">Warning</span>
                  The transcription failed to process. Try again.{' '}
                  <Link href="/contact" className="govuk-link">
                    Contact support
                  </Link>{' '}
                  if the issue persists.
                </strong>
              </div>
              <h2 className="govuk-heading-m">Audio:</h2>
              <AudioPlayer transcriptionId={transcription.id} />
              <div className="govuk-button-group govuk-!-margin-top-4">
                {recordings[0] && (
                  <RetryTranscriptionDialog
                    recordingId={recordings[0].id}
                    title={transcription.title ?? undefined}
                  />
                )}
                <DownloadButton recordings={recordings} />
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }
  // Ready: the redirect effect above sends the user to the latest summary
  // or the transcript page, so just show a loader in the meantime.
  return (
    <div className="govuk-!-padding-top-4 govuk-width-container govuk-width-container--with-secondary-nav">
      <div className="govuk-width-container">
        <div className="flex items-center gap-2">
          <Loader2 className="animate-spin" />
          <p className="govuk-body govuk-!-margin-bottom-0">Loading...</p>
        </div>
      </div>
    </div>
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
  return <audio controls src={recordings[0].url} className="w-full" />
}
