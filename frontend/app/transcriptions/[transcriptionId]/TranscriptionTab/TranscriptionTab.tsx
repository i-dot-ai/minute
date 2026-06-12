import { SpeakerEditor } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/SpeakerEditor'
import { SpeakerNamePopover } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/SpeakerNamePopover'
import { TranscriptionTextArea } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/TranscriptionTextArea'
import { DownloadButton } from '@/components/download-button'
import CopyButton from '@/components/ui/copy-button'
import { useSaveTranscription } from '@/hooks/use-save-transcription'
import { DialogueEntry, Transcription } from '@/lib/client'
import { getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { ArrowDown, Play } from 'lucide-react'
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
    <div className="govuk-grid-row">
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(saveTranscription)}>
          <div className="side-panel__sticky-container govuk-grid-column-one-third">
            <h2 className="govuk-heading-m">Speakers</h2>
            <SpeakerEditor
              transcription={transcription}
              src={hasRecordings ? recordings[0].url : undefined}
            />
            <p className="govuk-body">You can also click on the speaker&apos;s name to edit</p>
            <div className="side-panel__section-divider" />
            <h2 className="govuk-heading-m">Export</h2>
            <CopyButton
              textToCopy={transcriptionString}
              posthogEvent="transcript_content_copied"
            />
          </div>
          <div className="govuk-grid-column-two-thirds" style={{ borderLeft: '1px solid #b1b4b6' }}>
            {hasRecordings && (
              <div className="sticky top-0 bg-white govuk-!-margin-bottom-4" style={{ borderBottom: '1px solid #b1b4b6' }}>
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
                <div className="govuk-button-group govuk-!-margin-top-2">
                  <DownloadButton recordings={recordings} />
                  <button onClick={scrollToPlaying} className="govuk-button govuk-button--secondary">
                    <ArrowDown /> Scroll to playing
                  </button>
                </div>
              </div>
            )}
            <div className="flex flex-col gap-6">
              {fields.map((entry, index, array) => {
                const isPlaying =
                  time &&
                  time >= entry.start_time &&
                  (!array[index + 1] || time < array[index + 1].start_time)
                return (
                  <div
                    className={isPlaying ? 'bg-blue-100' : ''}
                    key={entry.id}
                    ref={isPlaying ? playingRef : null}
                  >
                    <div className="flex justify-between">
                      <p className="govuk-body govuk-!-font-weight-bold">{entry.speaker}:</p>
                      <div className="govuk-button-group govuk-!-margin-right-0">
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
                            className="govuk-button govuk-button--secondary"
                          >
                            <Play />
                            Play
                          </button>
                        )}
                        <SpeakerNamePopover
                          entry={entry}
                          index={index}
                          update={update}
                        />
                      </div>
                    </div>
                    <TranscriptionTextArea control={control} index={index} />
                  </div>
                )
              })}
            </div>
          </div>
        </form>
      </FormProvider>
    </div>
  )
}
