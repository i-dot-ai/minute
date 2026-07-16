'use client'

import { SpeakerEditor } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/SpeakerEditor'
import { SpeakerNamePopover } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/SpeakerNamePopover'
import { TranscriptionTextArea } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/TranscriptionTextArea'
import { DialogueEntryForm } from '@/types/transcriptions'
import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
import { ExportTranscriptDialog } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/ExportTranscriptDialog'
import { formatTime } from '@/components/audio/audio-player'
import { useRenameTranscription } from '@/components/recent-meetings/rename-transcription'
import { useSaveTranscription } from '@/hooks/use-save-transcription'
import {
  getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions,
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { ArrowDown, Loader2, Pencil, Play, Save } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useMemo, useRef, useState } from 'react'
import { FormProvider, useFieldArray, useForm } from 'react-hook-form'

export default function TranscriptPage({
  params: { transcriptionId },
}: {
  params: { transcriptionId: string }
}) {
  const router = useRouter()
  const { data: transcription, isLoading } = useQuery({
    ...getTranscriptionTranscriptionsTranscriptionIdGetOptions({
      path: { transcription_id: transcriptionId },
    }),
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
      <div className="govuk-main-wrapper">
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-full">
            <div className="flex items-center gap-2">
              <Loader2 className="animate-spin" />
              <p className="govuk-body govuk-!-margin-bottom-0">Loading...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!transcription) {
    return (
      <div className="govuk-main-wrapper">
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-full">
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
        </div>
      </div>
    )
  }

  return (
    <div className="govuk-grid-row">
      <FormProvider {...methods}>
        <div className="govuk-grid-column-full">
          <div className="sticky top-0 z-10 bg-white">
            <div className="govuk-!-padding-bottom-4 govuk-!-padding-top-8 flex justify-between">
              <div className="govuk-button-group govuk-!-margin-bottom-0">
                <NewMinuteDialog
                  transcriptionId={transcriptionId}
                  onCreated={() =>
                    router.push(`/transcriptions/${transcriptionId}/summary`)
                  }
                />
              </div>
              <div className="govuk-button-group govuk-!-margin-bottom-0 justify-end">
                <button
                  type="button"
                  className="govuk-button govuk-button--secondary"
                  onClick={() => {
                    setDraftTitle(transcription.title ?? '')
                    setIsRenaming(true)
                  }}
                >
                  <Pencil className="size-4" /> Edit
                </button>
                <ExportTranscriptDialog
                  transcriptionString={transcriptionString}
                  recordings={recordings}
                />
                <SpeakerEditor
                  transcription={transcription}
                  src={hasRecordings ? recordings[0].url : undefined}
                />
              </div>
            </div>
            {hasRecordings && (
              <div className="govuk-!-padding-bottom-4">
                <div className="flex">
                  <audio
                    controls
                    src={recordings[0].url}
                    className="w-full"
                    ref={audioRef}
                    onSeeked={delayedScroll}
                    onTimeUpdate={(e) => {
                      if ((e.target as HTMLAudioElement).currentTime != null) {
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
                      <ArrowDown className="size-4" /> Scroll to current section
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
          {isRenaming ? (
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
          ) : (
            <>
              <h1 className="govuk-heading-m">{transcription.title}</h1>
            </>
          )}
          <div
            className="govuk-visually-hidden"
            role="status"
            aria-live="polite"
          >
            {saveMessage}
          </div>
          <form onSubmit={handleSubmit(saveTranscription)}>
            <div className="flex flex-col gap-6">
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
                                audioRef.current.currentTime = entry.start_time
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
      </FormProvider>
    </div>
  )
}
