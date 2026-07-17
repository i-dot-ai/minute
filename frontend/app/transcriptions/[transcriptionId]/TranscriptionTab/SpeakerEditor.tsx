'use client'

import { DialogueEntryForm } from '@/types/transcriptions'
import { formatTime } from '@/components/audio/audio-player'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { useSaveTranscription } from '@/hooks/use-save-transcription'
import { DialogueEntry, Transcription } from '@/lib/client'
import { Pause, Play, Save, User } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useFieldArray, useFormContext } from 'react-hook-form'

export const SpeakerEditor = ({
  transcription,
  src,
  onSaved,
}: {
  transcription: Transcription
  src?: string
  onSaved?: (data: DialogueEntryForm) => void
}) => {
  const { saveTranscription } = useSaveTranscription(transcription.id!)

  const form = useFormContext<DialogueEntryForm>()
  const entries = form.watch('entries')
  const fieldArray = useFieldArray({ control: form.control, name: 'entries' })
  const [open, setOpen] = useState(false)
  const [draftNames, setDraftNames] = useState<Record<string, string>>({})

  const speakers = useMemo(() => {
    const speakerMap: Map<string, DialogueEntry[]> = new Map<
      string,
      DialogueEntry[]
    >()
    entries?.forEach((entry) => {
      speakerMap.set(entry.speaker, [
        ...(speakerMap.get(entry.speaker) || []),
        entry,
      ])
    })
    return speakerMap
  }, [entries])

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (nextOpen) {
        const names: Record<string, string> = {}
        entries?.forEach((entry) => {
          if (!(entry.speaker in names)) {
            names[entry.speaker] = entry.speaker
          }
        })
        setDraftNames(names)
      }
      setOpen(nextOpen)
    },
    [entries]
  )

  const handleSaveAll = useCallback(() => {
    Object.entries(draftNames).forEach(([originalSpeaker, newSpeaker]) => {
      const trimmed = newSpeaker.trim()
      if (!trimmed || trimmed === originalSpeaker) return

      form
        .getValues('entries')
        .map((e, i) => ({
          ...e,
          i,
        }))
        .filter((e) => e.speaker === originalSpeaker)
        .forEach(({ i, ...entry }) => {
          fieldArray.update(i, { ...entry, speaker: trimmed })
        })
    })
    form.handleSubmit(async (data) => {
      try {
        await saveTranscription(data)
        setOpen(false)
        onSaved?.(data)
      } catch {
        // keep dialog open so changes are not lost
      }
    })()
  }, [draftNames, fieldArray, form, onSaved, saveTranscription])

  const handleCancel = useCallback(() => {
    setOpen(false)
  }, [])

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <button type="button" className="govuk-button govuk-button--secondary">
          <User className="size-4" />
          Edit all speaker names
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle className="govuk-heading-m">
          Edit speaker names
        </DialogTitle>
        <DialogDescription className="govuk-body">
          You can edit speaker names here or on the transcript. Click on the
          speaker&apos;s name to edit
        </DialogDescription>
        <div className="max-h-[50vh] overflow-x-hidden overflow-y-auto">
          <ul>
            {Array.from(speakers.entries()).map(
              ([speaker, speakerEntries], index) => (
                <li key={speaker} className="govuk-!-margin-bottom-4">
                  <SpeakerNameField
                    label={`Speaker ${index + 1}`}
                    inputId={`speaker-name-${index}`}
                    value={draftNames[speaker] ?? speaker}
                    onChange={(value) =>
                      setDraftNames((prev) => ({ ...prev, [speaker]: value }))
                    }
                  />
                  <ul className="govuk-button-group govuk-!-margin-top-2">
                    {src &&
                      speakerEntries.slice(0, 3).map((entry) => (
                        <li key={entry.start_time}>
                          <PlayClipButton
                            src={src}
                            startTime={entry.start_time}
                            endTime={entry.end_time}
                          />
                        </li>
                      ))}
                  </ul>
                </li>
              )
            )}
          </ul>
        </div>
        <div className="govuk-button-group govuk-!-margin-top-4 justify-end">
          <button
            type="button"
            className="govuk-link text-(--govuk-link-colour)"
            onClick={handleCancel}
          >
            Cancel
          </button>
          <button
            type="button"
            className="govuk-button"
            onClick={handleSaveAll}
          >
            <Save className="size-4" /> Save all
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

const SpeakerNameField = ({
  label,
  inputId,
  value,
  onChange,
}: {
  label: string
  inputId: string
  value: string
  onChange: (value: string) => void
}) => (
  <div className="govuk-form-group govuk-!-margin-bottom-0">
    <div className="govuk-label-wrapper">
      <label className="govuk-label govuk-label--s" htmlFor={inputId}>
        {label}
      </label>
    </div>
    <input
      className="govuk-input"
      id={inputId}
      name={inputId}
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  </div>
)

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
    <button
      type="button"
      className="govuk-button govuk-button--secondary"
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
      <span className="govuk-visually-hidden">
        {isPlaying ? 'Pause clip' : 'Play clip'}
      </span>
      {formatTime(startTime)}
    </button>
  )
}
