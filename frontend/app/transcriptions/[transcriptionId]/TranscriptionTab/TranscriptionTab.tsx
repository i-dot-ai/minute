import { SpeakerEditor } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/SpeakerEditor'
import { SpeakerNamePopover } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/SpeakerNamePopover'
import { TranscriptionTextArea } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/TranscriptionTextArea'
import { DownloadButton } from '@/components/download-button'
import { Button } from '@/components/ui/button'
import CopyButton from '@/components/ui/copy-button'
import { useSaveTranscription } from '@/hooks/use-save-transcription'
import { DialogueEntry, Transcription } from '@/lib/client'
import { getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { cn } from '@/lib/utils'
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
    <div>
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(saveTranscription)}>
          <div className="flex justify-between">
            <SpeakerEditor
              transcription={transcription}
              src={hasRecordings ? recordings[0].url : undefined}
            />
            <CopyButton
              textToCopy={transcriptionString}
              posthogEvent="transcript_content_copied"
            />
          </div>
          {hasRecordings && (
            <div className="sticky top-0 mb-2 flex flex-col gap-2 rounded border bg-white p-2">
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
              <div className="flex justify-between">
                <div>
                  {playingRef.current && (
                    <Button onClick={scrollToPlaying} variant="link">
                      <ArrowDown /> Scroll to playing
                    </Button>
                  )}
                </div>
                <DownloadButton recordings={recordings} />
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
                  className={cn('flex items-start gap-2 rounded', {
                    'bg-blue-100': isPlaying,
                  })}
                  key={entry.id}
                  ref={isPlaying ? playingRef : null}
                >
                  {hasRecordings && (
                    <Button
                      type="button"
                      onClick={() => {
                        if (audioRef.current) {
                          audioRef.current.currentTime = entry.start_time
                          if (audioRef.current.paused) {
                            audioRef.current.play()
                          }
                        }
                      }}
                      variant="ghost"
                      className="size-6 rounded-full bg-blue-500 text-xs text-white hover:bg-blue-800 hover:text-white"
                      size="icon"
                    >
                      <Play />
                    </Button>
                  )}
                  <SpeakerNamePopover
                    entry={entry}
                    index={index}
                    update={update}
                  />
                  <TranscriptionTextArea control={control} index={index} />
                </div>
              )
            })}
          </div>
        </form>
      </FormProvider>
    </div>
  )
}
