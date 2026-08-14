'use client'

import { SpeakerEditor } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/SpeakerEditor'
import { SpeakerNamePopover } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/SpeakerNamePopover'
import { DialogueEntryForm } from '@/types/transcriptions'
// import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
import { ExportTranscriptDialog } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/ExportTranscriptDialog'
import { formatTime } from '@/components/audio/audio-player'
import { useRenameTranscription } from '@/components/recent-meetings/rename-transcription'
import { useSaveTranscription } from '@/hooks/use-save-transcription'
import {
  getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions,
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowDown,
  Loader2,
  Pause,
  Pencil,
  Play,
  Save,
  CircleUserRound,
  CircleArrowRight,
} from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import posthog from 'posthog-js'
import { use, useEffect, useMemo, useRef, useState } from 'react'
import { FormProvider, useFieldArray, useForm } from 'react-hook-form'
import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'

export default function TranscriptPage({
  params,
}: {
  params: Promise<{ transcriptionId: string }>
}) {
  const { transcriptionId } = use(params)
  const router = useRouter()
  const { data: transcription, isLoading } = useQuery({
    ...getTranscriptionTranscriptionsTranscriptionIdGetOptions({
      path: { transcription_id: transcriptionId },
    }),
  })

  const [isEditing, setIsEditing] = useState(false)
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
    register,
    handleSubmit,
    formState: { dirtyFields },
    reset,
  } = methods

  const transcriptionString = useMemo(
    () =>
      (transcription?.dialogue_entries || [])
        .map((entry) => `<p><b>${entry.speaker}:</b> ${entry.text}</p>`)
        .join('\n\n'),
    [transcription?.dialogue_entries]
  )

  useEffect(() => {
    reset({ entries: transcription?.dialogue_entries || [] })
  }, [reset, transcription?.dialogue_entries])

  const { saveTranscription } = useSaveTranscription(transcriptionId)

  const handleSave = handleSubmit(async (data) => {
    try {
      await saveTranscription(data)
      if (dirtyFields.entries) {
        posthog.capture('transcript_text_edited')
      }
      if (draftTitle !== (transcription?.title ?? '')) {
        saveTitle(draftTitle)
      }
      reset(data)
      setIsEditing(false)
    } catch {
      // keep edit mode open so changes are not lost
    }
  })

  const handleDiscard = () => {
    reset({ entries: transcription?.dialogue_entries || [] })
    setIsEditing(false)
  }

  const { fields, update } = useFieldArray({ control, name: 'entries' })

  const { data: recordings } = useQuery({
    ...getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions(
      { path: { transcription_id: transcriptionId } }
    ),
  })

  const audioEls = useRef<Set<HTMLAudioElement>>(new Set())
  const playingRef = useRef<HTMLDivElement | null>(null)
  const [time, setTime] = useState(0)
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)

  const registerAudio = (el: HTMLAudioElement | null) => {
    if (el) {
      audioEls.current.add(el)
    }
  }

  const getAudioEls = () => {
    const els = [...audioEls.current].filter((el) => el.isConnected)
    audioEls.current = new Set(els)
    return els
  }

  // The page renders separate audio elements for desktop and mobile layouts,
  // so playback must always target the one that is currently visible
  const getActiveAudio = () => {
    const els = getAudioEls()
    return els.find((el) => el.offsetParent !== null) ?? els[0] ?? null
  }

  const audioHandlers = {
    onSeeked: () => delayedScroll(),
    onTimeUpdate: (e: React.SyntheticEvent<HTMLAudioElement>) =>
      setTime(e.currentTarget.currentTime),
    onPlay: (e: React.SyntheticEvent<HTMLAudioElement>) => {
      const current = e.currentTarget
      getAudioEls().forEach((el) => {
        if (el !== current && !el.paused) {
          el.pause()
        }
      })
      setIsAudioPlaying(true)
    },
    onPause: () => setIsAudioPlaying(getAudioEls().some((el) => !el.paused)),
  }

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
      <div className="govuk-main-wrapper govuk-width-container govuk-width-container--with-secondary-nav">
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
      <div className="govuk-main-wrapper govuk-width-container govuk-width-container--with-secondary-nav">
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
    <FormProvider {...methods}>
      <div className="flex h-full flex-col">
        <div className="govuk-!-padding-bottom-4 govuk-!-padding-top-4 shrink-0 border-b border-(--govuk-border-colour) bg-white">
          <div className="govuk-width-container govuk-width-container--with-secondary-nav">
            <div className="sm:flex sm:items-center sm:justify-between">
              {!isEditing ? (
                <nav
                  className="govuk-breadcrumbs govuk-!-margin-top-2 sm:mb-0"
                  aria-label="Breadcrumb"
                >
                  <ol className="govuk-breadcrumbs__list">
                    <li className="govuk-breadcrumbs__list-item">
                      <Link
                        className="govuk-breadcrumbs__link"
                        href="/transcriptions"
                      >
                        Back
                      </Link>
                    </li>
                  </ol>
                </nav>
              ) : (
                <div className="govuk-button-group govuk-!-margin-bottom-0">
                  <SpeakerEditor
                    transcription={transcription}
                    src={hasRecordings ? recordings[0].url : undefined}
                    onSaved={(data) => {
                      reset(data)
                      setIsEditing(false)
                    }}
                  />
                </div>
              )}
              {hasRecordings && (
                <audio
                  controls
                  src={recordings[0].url}
                  className="govuk-!-margin-left-4 govuk-!-margin-right-4 hidden max-h-11 flex-1 xl:block"
                  ref={registerAudio}
                  {...audioHandlers}
                />
              )}
              {!isEditing ? (
                <div className="govuk-button-group govuk-!-margin-bottom-0 justify-end">
                  {hasRecordings && (
                    <div className="hidden xl:block">
                      <button
                        type="button"
                        onClick={scrollToPlaying}
                        className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0"
                      >
                        <ArrowDown className="size-4" /> Scroll to current
                        section
                      </button>
                    </div>
                  )}
                  <Link
                    href={`/transcriptions/${transcriptionId}/summary`}
                    className="govuk-button sm:!hidden"
                  >
                    <CircleArrowRight className="size-4" /> Go to summary
                  </Link>
                  <NewMinuteDialog
                    transcriptionId={transcriptionId}
                    icon
                    buttonClassName="govuk-button govuk-button--secondary sm:!hidden"
                    onCreated={() =>
                      router.push(
                        `/transcriptions/${transcriptionId}/transcript`
                      )
                    }
                  />
                  <ExportTranscriptDialog
                    transcriptionString={transcriptionString}
                    recordings={recordings}
                  />
                  <button
                    type="button"
                    className="govuk-button govuk-!-margin-bottom-0 !hidden sm:!flex"
                    onClick={() => {
                      setDraftTitle(transcription.title ?? '')
                      setIsEditing(true)
                    }}
                  >
                    <Pencil className="size-4" /> Edit
                  </button>
                  <button
                    type="button"
                    className="govuk-button govuk-button--secondary sm:!hidden"
                    onClick={() => {
                      setDraftTitle(transcription.title ?? '')
                      setIsEditing(true)
                    }}
                  >
                    <Pencil className="size-4" /> Edit
                  </button>
                </div>
              ) : (
                <div className="govuk-button-group govuk-!-margin-bottom-0 justify-end">
                  <button
                    type="button"
                    className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0"
                    onClick={handleDiscard}
                  >
                    Discard
                  </button>
                  <button
                    type="button"
                    className="govuk-button govuk-!-margin-bottom-0"
                    onClick={handleSave}
                    disabled={isSavingTitle}
                  >
                    <Save className="size-4" /> Save
                  </button>
                </div>
              )}
            </div>
            {hasRecordings && (
              <div className="govuk-!-margin-top-4 flex xl:hidden">
                <audio
                  controls
                  src={recordings[0].url}
                  className="max-h-11 w-full"
                  ref={registerAudio}
                  {...audioHandlers}
                />
                <div className="govuk-!-margin-top-1 govuk-!-margin-left-3 hidden sm:block">
                  <button
                    type="button"
                    onClick={scrollToPlaying}
                    className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0 whitespace-nowrap"
                  >
                    <ArrowDown className="size-4" /> Scroll to current section
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
        <div
          className={`min-h-0 flex-1 overflow-y-auto ${isEditing ? 'bg-(--govuk-surface-background-colour)' : ''}`}
        >
          <div className="govuk-width-container govuk-width-container--with-secondary-nav">
            {isEditing ? (
              <div className="govuk-form-group govuk-!-padding-top-4">
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
                  className="govuk-input bg-white"
                  type="text"
                  placeholder="Add title"
                  value={draftTitle}
                  onChange={(e) => setDraftTitle(e.target.value)}
                />
              </div>
            ) : (
              <h1 className="govuk-heading-m govuk-!-margin-top-4">
                {transcription.title}
              </h1>
            )}
            <form onSubmit={handleSave}>
              <div className="flex flex-col gap-6">
                {fields.map((entry, index, array) => {
                  const isPlaying =
                    time &&
                    time >= entry.start_time &&
                    (!array[index + 1] || time < array[index + 1].start_time)
                  return (
                    <div
                      className={`govuk-!-margin-bottom-4 govuk-!-padding-4 ${isPlaying ? 'bg-[#d2e2f1]' : ''}`}
                      key={index}
                      ref={isPlaying ? playingRef : null}
                    >
                      <div className="flex justify-between">
                        <div className="govuk-!-margin-bottom-3 govuk-!-padding-top-1 flex items-center gap-2">
                          <CircleUserRound />
                          <h2
                            className={`govuk-heading-s govuk-!-margin-bottom-0 ${isPlaying ? '' : 'govuk-!-font-weight-regular'}`}
                          >
                            {entry.speaker}
                          </h2>

                          {isEditing && (
                            <SpeakerNamePopover
                              entry={entry}
                              index={index}
                              update={update}
                            />
                          )}
                        </div>
                        <div className="govuk-button-group govuk-!-margin-right-0 govuk-!-margin-bottom-0">
                          {hasRecordings && (
                            <button
                              type="button"
                              onClick={() => {
                                const audio = getActiveAudio()
                                if (!audio) return
                                if (isPlaying && !audio.paused) {
                                  audio.pause()
                                  return
                                }
                                if (!isPlaying) {
                                  audio.currentTime = entry.start_time
                                }
                                audio.play()
                              }}
                              className={`govuk-button ${isPlaying ? 'govuk-button--inverse' : 'govuk-button--secondary'}`}
                            >
                              {isPlaying && isAudioPlaying ? (
                                <Pause className="size-4" />
                              ) : (
                                <Play className="size-4" />
                              )}
                              <span className="govuk-visually-hidden">
                                {isPlaying && isAudioPlaying
                                  ? 'Pause section from '
                                  : 'Play section from '}
                              </span>
                              {formatTime(entry.start_time)}
                            </button>
                          )}
                        </div>
                      </div>
                      {isEditing ? (
                        <textarea
                          className="govuk-textarea govuk-!-margin-bottom-0 bg-white"
                          id={`transcript-entry-${index}`}
                          aria-label={`Transcript text for entry ${index + 1}`}
                          {...register(`entries.${index}.text`)}
                        />
                      ) : (
                        <p className="govuk-body govuk-!-margin-bottom-0">
                          {entry.text}
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            </form>
          </div>
        </div>
      </div>
    </FormProvider>
  )
}
