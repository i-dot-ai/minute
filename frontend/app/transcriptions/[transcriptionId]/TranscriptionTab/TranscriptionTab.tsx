import { SpeakerEditor } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/SpeakerEditor'
import { SpeakerNamePopover } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/SpeakerNamePopover'
import { TranscriptionTextArea } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/TranscriptionTextArea'
import { DownloadButton } from '@/components/download-button'
import CopyButton from '@/components/ui/copy-button'
import { formatTime } from '@/components/audio/audio-player'
import { useSaveTranscription } from '@/hooks/use-save-transcription'
import { DialogueEntry, Transcription } from '@/lib/client'
import { getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { ArrowDown, PencilIcon, Play, SquarePen } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { FormProvider, useFieldArray, useForm } from 'react-hook-form'

export type DialogueEntryForm = {
  entries: DialogueEntry[]
}

export function TranscriptionTab({
  transcription,
}: {
  transcription: Transcription
}) {
  const methods = useForm<DialogueEntryForm>({
    defaultValues: { entries: transcription.dialogue_entries || [] },
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
      (transcription.dialogue_entries || [])
        .map((entry) => `<p><b>${entry.speaker}:</b> ${entry.text}</p>`)
        .join('\n\n'),
    [transcription.dialogue_entries]
  )

  useEffect(() => {
    setValue('entries', transcription.dialogue_entries || [])
  }, [setValue, transcription.dialogue_entries])

  const { saveTranscription } = useSaveTranscription(transcription.id!)
  useEffect(() => {
    if (isDirty) {
      handleSubmit(saveTranscription)()
      reset(watch())
    }
  }, [handleSubmit, isDirty, saveTranscription, reset, watch])

  const { fields, update } = useFieldArray({ control, name: 'entries' })

  const { data: recordings } = useQuery({
    ...getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions(
      { path: { transcription_id: transcription.id! } }
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

  return (
    <FormProvider {...methods}>
      <form onSubmit={handleSubmit(saveTranscription)}>
        <div className="bg-[#8eb8dc] px-[20px] pt-[30px] pb-[10px] sm:mx-[-20px] sm:mt-[-30px]">
          <div className="govuk-grid-row">
            <div className="govuk-grid-column-two-thirds">
              <div className="govuk-button-group govuk-!-margin-bottom-0">
                <SpeakerEditor
                  transcription={transcription}
                  src={hasRecordings ? recordings[0].url : undefined}
                />
                <CopyButton
                  textToCopy={transcriptionString}
                  posthogEvent="transcript_content_copied"
                />
                {hasRecordings && (
                  <DownloadButton recordings={recordings} inverse={true} />
                )}
              </div>
              <p className="govuk-body-s govuk-!-margin-bottom-1">
                If you rename a speaker, you must re-generate the summary to use
                the new names.
              </p>
            </div>
            <div className="govuk-grid-column-one-third">
              <div>
                <p className="govuk-body-s govuk-!-margin-bottom-1 flex gap-2">
                  <PencilIcon className="inline-block size-4" /> Click a name to
                  rename it.
                </p>
                <p className="govuk-body-s govuk-!-margin-bottom-1 flex gap-2">
                  <SquarePen className="inline-block size-4" /> Click any text
                  box to edit the text.
                </p>
                <p className="govuk-body-s govuk-!-margin-bottom-1 flex gap-2">
                  <Play className="inline-block size-4" /> Click a timestamp to
                  play from that point.
                </p>
              </div>
            </div>
          </div>
        </div>
        {hasRecordings && (
          <div className="sticky top-0 z-10 border-b border-(--govuk-border-colour) bg-[#8eb8dc] px-[20px] py-[10px] sm:mx-[-20px]">
            <div className="govuk-grid-row">
              <div className="govuk-grid-column-two-thirds">
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
              </div>
              <div className="govuk-grid-column-one-third">
                <div className="govuk-button-group govuk-!-margin-top-1 govuk-!-margin-bottom-0">
                  <button
                    type="button"
                    onClick={scrollToPlaying}
                    className="govuk-button govuk-button--inverse"
                  >
                    <ArrowDown className="size-4" /> Scroll to current section
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-full">
            <div className="flex flex-col gap-6">
              {fields.map((entry, index, array) => {
                const isPlaying =
                  time &&
                  time >= entry.start_time &&
                  (!array[index + 1] || time < array[index + 1].start_time)
                return (
                  <div
                    className={`transcription-text-area ${isPlaying ? 'transcription-text-area--playing' : ''}`}
                    key={entry.id}
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
          </div>
        </div>
      </form>
    </FormProvider>
  )
}
