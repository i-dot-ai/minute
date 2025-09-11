'use client'

import { DialogueEntryForm } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/TranscriptionTab'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { useSaveTranscription } from '@/hooks/use-save-transcription'
import { DialogueEntry, Transcription } from '@/lib/client'
import { Edit2, Pause, Play } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { FormProvider, useFieldArray, useFormContext } from 'react-hook-form'

export const SpeakerEditor = ({
  transcription,
  src,
}: {
  transcription: Transcription
  src?: string
}) => {
  const { saveTranscription } = useSaveTranscription(transcription.id!)

  const speakers = useMemo(() => {
    const speakerMap: Map<string, DialogueEntry[]> = new Map<
      string,
      DialogueEntry[]
    >()
    transcription.dialogue_entries?.forEach((entry) => {
      speakerMap.set(entry.speaker, [
        ...(speakerMap.get(entry.speaker) || []),
        entry,
      ])
    })
    return speakerMap
  }, [transcription.dialogue_entries])

  const form = useFormContext<DialogueEntryForm>()
  const fieldArray = useFieldArray({ control: form.control, name: 'entries' })
  const [selected, setSelected] = useState<string | undefined>()
  const onSave = useCallback(
    (originalSpeaker: string) => (newSpeaker: string) => {
      form
        .getValues('entries')
        .map((e, i) => ({
          ...e,
          i,
        }))
        .filter((e) => e.speaker === originalSpeaker)
        .forEach(({ i, ...entry }) => {
          fieldArray.update(i, { ...entry, speaker: newSpeaker })
        })
      form.handleSubmit(saveTranscription)()
    },
    [fieldArray, form, saveTranscription]
  )

  return (
    <Dialog>
      <DialogTrigger asChild className="mb-4">
        <Button className="active:bg-yellow-400">
          <Edit2 />
          View/Edit Speaker Names
        </Button>
      </DialogTrigger>
      <DialogContent className="scroll max-h-screen overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Edit speaker names</DialogTitle>
          <DialogDescription>
            You can edit speaker names here or on the transcript. Click on the
            speaker&apos;s name to edit
          </DialogDescription>
        </DialogHeader>
        <FormProvider {...form}>
          <form className="flex flex-col gap-2">
            {Array.from(speakers.entries()).map(([speaker, entries]) => (
              <div key={speaker} className="flex w-full justify-between gap-1">
                <SpeakerNameEditor
                  speaker={speaker}
                  onSave={onSave(speaker)}
                  selected={selected == speaker}
                  setSelected={setSelected}
                />
                <div className="flex gap-1">
                  {src &&
                    entries
                      .slice(0, 3)
                      .map((entry) => (
                        <PlayClipButton
                          key={entry.start_time}
                          src={src}
                          startTime={entry.start_time}
                          endTime={entry.end_time}
                        />
                      ))}
                </div>
              </div>
            ))}
          </form>
        </FormProvider>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Done</Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

const SpeakerNameEditor = ({
  speaker,
  onSave,
  selected,
  setSelected,
}: {
  speaker: string
  onSave: (name: string) => void
  selected: boolean
  setSelected: (n: string | undefined) => void
}) => {
  const [value, setValue] = useState(speaker)
  const inputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    if (selected && inputRef.current) {
      inputRef.current.focus()
    }
  }, [selected])

  if (!selected) {
    return (
      <Button
        onClick={() => {
          setSelected(speaker)
        }}
        variant="link"
        type="button"
      >
        <Edit2 /> {speaker}
      </Button>
    )
  }

  return (
    <div className="flex flex-1 gap-1">
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        ref={inputRef}
      />
      <Button
        type="button"
        variant="secondary"
        onClick={() => {
          setValue(speaker)
          setSelected(undefined)
        }}
      >
        Cancel
      </Button>
      <Button
        type="button"
        onClick={() => {
          onSave(value)
          setSelected(undefined)
        }}
      >
        Save
      </Button>
    </div>
  )
}

const PlayClipButton = ({
  src,
  startTime,
  endTime,
}: {
  src: string
  startTime: number
  endTime: number
}) => {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setPlaying] = useState(false)
  useEffect(() => {
    if (!audioRef.current) {
      audioRef.current = new Audio(src)
    }
    const audio = audioRef.current
    audio.currentTime = startTime
    const onPlay = () => {
      audio.currentTime = startTime
      setPlaying(true)
    }
    const onPause = () => {
      setPlaying(false)
    }
    const onTimeUpdate = () => {
      const current = audio.currentTime

      // Stop playback when we reach the end time
      if (current >= endTime) {
        audio.pause()
      }
    }
    audio.addEventListener('play', onPlay)
    audio.addEventListener('pause', onPause)
    audio.addEventListener('timeupdate', onTimeUpdate)
    return () => {
      audio.pause()
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('pause', onPause)
      audio.removeEventListener('timeupdate', onTimeUpdate)
    }
  }, [endTime, src, startTime])

  return (
    <Button
      type="button"
      className="size-8 rounded-full bg-blue-500 text-xs text-white hover:bg-blue-800 hover:text-white"
      onClick={() => {
        if (audioRef.current) {
          if (audioRef.current.paused) {
            audioRef.current.play()
          } else {
            audioRef.current.pause()
          }
        }
      }}
    >
      {isPlaying ? <Pause /> : <Play />}
    </Button>
  )
}
