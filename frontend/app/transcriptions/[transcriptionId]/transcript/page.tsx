'use client'

import { SpeakerEditor } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/SpeakerEditor'
import { SpeakerNamePopover } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/SpeakerNamePopover'
import { TranscriptionTextArea } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/TranscriptionTextArea'
import { DialogueEntryForm } from '@/types/transcriptions'
import { TranscriptionSidePanel } from '@/app/transcriptions/[transcriptionId]/MinuteTab/components/TranscriptionSidePanel'
import { ExportTranscriptDialog } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/ExportTranscriptDialog'
import { formatTime } from '@/components/audio/audio-player'
import { DeleteTranscriptionButton } from '@/components/recent-meetings/delete-transcription-button'
import { useRenameTranscription } from '@/components/recent-meetings/rename-transcription'
import { useSaveTranscription } from '@/hooks/use-save-transcription'
import {
  getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions,
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { ArrowDown, Loader2, Pencil, Play, Save } from 'lucide-react'
import Link from 'next/link'
import { useEffect, useMemo, useRef, useState } from 'react'
import { FormProvider, useFieldArray, useForm } from 'react-hook-form'

export default function TranscriptPage({
  params: { transcriptionId },
}: {
  params: { transcriptionId: string }
}) {
  const { data: transcription, isLoading } = useQuery({
    ...getTranscriptionTranscriptionsTranscriptionIdGetOptions({
      path: { transcription_id: transcriptionId },
    }),
  })

  const { data: minutes = [] } = useQuery({
    ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions(
      {
        path: { transcription_id: transcriptionId },
      }
    ),
  })

  const [isRenaming, setIsRenaming] = useState(false)
  const [draftTitle, setDraftTitle] = useState('')
  const { save: saveTitle, isPending: isSavingTitle } = useRenameTranscription({
    id: transcriptionId,
    title: transcription?.title,
    status: transcription?.status ?? 'completed',
  })

  const methods = useForm<DialogueEntryForm>({
    defaultValues: { entries: transcription?.dialogue_entries || [] },
    mode: 'onBlur',
  })
  const {
    control,
    handleSubmit,
    formState: { isDirty },
    reset,
    watch,
    setValue,
  } = methods

  const transcriptionString = useMemo(
    () =>
      (transcription?.dialogue_entries || [])
        .map((entry) => `<p><b>${entry.speaker}:</b> ${entry.text}</p>`)
        .join('\n\n'),
    [transcription?.dialogue_entries]
  )

  useEffect(() => {
    setValue('entries', transcription?.dialogue_entries || [])
  }, [setValue, transcription?.dialogue_entries])

  const { saveTranscription } = useSaveTranscription(transcriptionId)
  const [saveMessage, setSaveMessage] = useState('')
  useEffect(() => {
    if (isDirty) {
      setSaveMessage('')
      handleSubmit(async (data) => {
        try {
          await saveTranscription(data)
          setSaveMessage('Changes saved')
        } catch {
          setSaveMessage('Could not save changes. Try again.')
        }
      })()
      reset(watch())
    }
  }, [handleSubmit, isDirty, saveTranscription, reset, watch])

  const { fields, update } = useFieldArray({ control, name: 'entries' })

  const { data: recordings } = useQuery({
    ...getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions(
      { path: { transcription_id: transcriptionId } }
    ),
  })

  const audioRef = useRef<HTMLAudioElement | null>(null)
  const playingRef = useRef<HTMLDivElement | null>(null)
  const [time, setTime] = useState(0)

  const scrollToPlaying = () => {
    if (playingRef.current) {
      playingRef.current.scrollIntoView({
        block: 'center',
        behavior: 'smooth',
      })
    }
  }

  const hasRecordings = !!recordings && !!recordings.length

  const delayedScroll = () =>
    new Promise((resolve) => setTimeout(resolve, 100)).then(scrollToPlaying)

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

  return (
    <div className="flex min-h-0 flex-1">
      <div className="w-1/4 shrink-0 pr-6">
        <TranscriptionSidePanel
          transcriptionId={transcriptionId}
          minutes={minutes}
          transcriptPage={true}
        />
      </div>
      <FormProvider {...methods}>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="govuk-!-padding-bottom-3 flex shrink-0 justify-between border-b border-(--govuk-border-colour)">
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
            <div className="govuk-button-group govuk-!-margin-bottom-0 justify-end">
              <button
                type="button"
                className="govuk-button govuk-button--secondary"
                onClick={() => {
                  setDraftTitle(transcription.title ?? '')
                  setIsRenaming(true)
                }}
              >
                <Pencil className="size-4" /> Rename
              </button>
              <ExportTranscriptDialog
                transcriptionString={transcriptionString}
                recordings={recordings}
              />
              <SpeakerEditor
                transcription={transcription}
                src={hasRecordings ? recordings[0].url : undefined}
              />
              <DeleteTranscriptionButton transcription={transcription} />
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto">
            {isRenaming ? (
              <div className="govuk-form-group govuk-!-padding-top-6">
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
                    type="button"
                    className="govuk-button"
                    disabled={isSavingTitle}
                    onClick={() => {
                      saveTitle(draftTitle)
                      setIsRenaming(false)
                    }}
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
              </div>
            ) : (
              <>
                <h1 className="govuk-heading-l govuk-!-margin-bottom-2 govuk-!-padding-top-6">
                  {transcription.title}
                </h1>
              </>
            )}
            <p className="govuk-body">{date}</p>
            <div
              className="govuk-visually-hidden"
              role="status"
              aria-live="polite"
            >
              {saveMessage}
            </div>
            <form onSubmit={handleSubmit(saveTranscription)}>
              {hasRecordings && (
                <div className="govuk-!-margin-bottom-6 govuk-!-padding-bottom-4 govuk-!-padding-top-2 sticky top-0 z-10 border-b border-(--govuk-border-colour) bg-white">
                  <div className="flex">
                    <audio
                      controls
                      src={recordings[0].url}
                      className="w-full"
                      ref={audioRef}
                      onSeeked={delayedScroll}
                      onTimeUpdate={(e) => {
                        if (
                          (e.target as HTMLAudioElement).currentTime != null
                        ) {
                          setTime((e.target as HTMLAudioElement).currentTime)
                        }
                      }}
                    />
                    <div className="govuk-button-group govuk-!-margin-top-1 govuk-!-margin-left-3 govuk-!-margin-bottom-0">
                      <button
                        type="button"
                        onClick={scrollToPlaying}
                        className="govuk-button govuk-button--secondary whitespace-nowrap"
                      >
                        <ArrowDown className="size-4" /> Scroll to current
                        section
                      </button>
                    </div>
                  </div>
                </div>
              )}
              <div className="govuk-!-padding-bottom-8 flex flex-col gap-6">
                {fields.map((entry, index, array) => {
                  const isPlaying =
                    time &&
                    time >= entry.start_time &&
                    (!array[index + 1] || time < array[index + 1].start_time)
                  return (
                    <div
                      className={`transcription-text-area ${isPlaying ? 'transcription-text-area--playing' : ''}`}
                      key={index}
                      ref={isPlaying ? playingRef : null}
                    >
                      <div className="flex justify-between">
                        <SpeakerNamePopover
                          entry={entry}
                          index={index}
                          update={update}
                        />
                        <div className="govuk-button-group govuk-!-margin-right-0 govuk-!-margin-bottom-0">
                          {hasRecordings && (
                            <button
                              type="button"
                              onClick={() => {
                                if (audioRef.current) {
                                  audioRef.current.currentTime =
                                    entry.start_time
                                  if (audioRef.current.paused) {
                                    audioRef.current.play()
                                  }
                                }
                              }}
                              className="play-section-trigger govuk-link govuk-link--no-visited-state govuk-!-margin-top-4 govuk-!-margin-bottom-4"
                            >
                              <Play className="size-4" />
                              <span className="govuk-visually-hidden">
                                Play section from{' '}
                              </span>
                              {formatTime(entry.start_time)}
                            </button>
                          )}
                        </div>
                      </div>
                      <TranscriptionTextArea control={control} index={index} />
                    </div>
                  )
                })}
              </div>
            </form>
          </div>
        </div>
      </FormProvider>
    </div>
  )
}
