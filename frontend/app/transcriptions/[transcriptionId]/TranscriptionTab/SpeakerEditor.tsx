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
import { useGenerateSummaryFromMinute } from '@/hooks/use-generate-summary-from-minute'
import { useSaveTranscription } from '@/hooks/use-save-transcription'
import { DialogueEntry, Transcription } from '@/lib/client'
import { listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { Loader2, Pause, Play, User } from 'lucide-react'
import { toast } from 'sonner'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useFieldArray, useFormContext } from 'react-hook-form'

export type SpeakerRenames = Record<string, string>

export const applySpeakerRenames = (
  entries: DialogueEntry[],
  renames: SpeakerRenames
): DialogueEntry[] =>
  entries.map((entry) => {
    const trimmed = renames[entry.speaker]?.trim()
    return trimmed && trimmed !== entry.speaker
      ? { ...entry, speaker: trimmed }
      : entry
  })

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
  const { generateSummary, isGenerating } = useGenerateSummaryFromMinute(
    transcription.id!
  )
  const { data: minutes = [] } = useQuery({
    ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions(
      { path: { transcription_id: transcription.id! } }
    ),
  })

  const form = useFormContext<DialogueEntryForm>()
  const entries = form.watch('entries')
  const fieldArray = useFieldArray({ control: form.control, name: 'entries' })
  const [open, setOpen] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const latestMinuteId = useMemo(
    () =>
      minutes.length
        ? minutes.reduce((latest, minute) =>
            new Date(minute.created_datetime) >
            new Date(latest.created_datetime)
              ? minute
              : latest
          ).id
        : null,
    [minutes]
  )

  const handleSave = useCallback(
    (renames: SpeakerRenames, generateNewSummary: boolean) => {
      Object.entries(renames).forEach(([originalSpeaker, newSpeaker]) => {
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
        setIsSaving(true)
        try {
          await saveTranscription(data)
          if (generateNewSummary) {
            await generateSummary(latestMinuteId)
            toast.success(
              <div className="flex flex-col items-center gap-2">
                <h2 className="govuk-heading-s">
                  New summary is being generated
                </h2>
                <strong className="govuk-tag govuk-tag--blue">
                  Processing
                </strong>
              </div>,
              {
                className: '!w-[420px] !max-w-[calc(100vw-2rem)] !p-5',
                duration: 6000,
              }
            )
          }
          setOpen(false)
          onSaved?.(data)
        } catch {
          // keep dialog open so changes are not lost
        } finally {
          setIsSaving(false)
        }
      })()
    },
    [
      fieldArray,
      form,
      generateSummary,
      latestMinuteId,
      onSaved,
      saveTranscription,
    ]
  )

  return (
    <SpeakerEditorDialog
      entries={entries ?? []}
      src={src}
      open={open}
      onOpenChange={setOpen}
      isBusy={isSaving || isGenerating}
      onSaveTranscriptOnly={(renames) => handleSave(renames, false)}
      onSaveAndGenerate={(renames) => handleSave(renames, true)}
      trigger={
        <DialogTrigger asChild>
          <button
            type="button"
            className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0"
          >
            <User className="size-4" />
            Edit speaker names
          </button>
        </DialogTrigger>
      }
    />
  )
}

export const SpeakerEditorDialog = ({
  entries,
  src,
  open,
  onOpenChange,
  description,
  isBusy,
  onSaveTranscriptOnly,
  onSaveAndGenerate,
  cancelLabel = 'Cancel',
  trigger,
}: {
  entries: DialogueEntry[]
  src?: string
  open: boolean
  onOpenChange: (open: boolean) => void
  description?: string
  isBusy: boolean
  onSaveTranscriptOnly?: (renames: SpeakerRenames) => void
  onSaveAndGenerate: (renames: SpeakerRenames) => void
  cancelLabel?: string
  trigger?: React.ReactNode
}) => {
  const [draftNames, setDraftNames] = useState<SpeakerRenames>({})

  // Reset drafts whenever the dialog opens, whether via the trigger or an
  // external `open` state change
  const prevOpen = useRef(false)
  useEffect(() => {
    if (open && !prevOpen.current) {
      const names: Record<string, string> = {}
      entries?.forEach((entry) => {
        if (!(entry.speaker in names)) {
          names[entry.speaker] = entry.speaker
        }
      })
      setDraftNames(names)
    }
    prevOpen.current = open
  }, [entries, open])

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

  const handleCancel = useCallback(() => {
    onOpenChange(false)
  }, [onOpenChange])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {trigger}
      <DialogContent>
        <DialogTitle className="govuk-heading-m govuk-!-margin-bottom-0">
          Edit speaker names
        </DialogTitle>
        <DialogDescription className="govuk-body govuk-!-margin-bottom-0">
          {description ??
            'Choose whether to save the transcript only or save and create a new summary.'}
        </DialogDescription>
        <div className="govuk-!-padding-1 max-h-[50vh] overflow-x-hidden overflow-y-auto">
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
            className="govuk-button govuk-button--secondary"
            onClick={handleCancel}
            disabled={isBusy}
          >
            {cancelLabel}
          </button>
          {onSaveTranscriptOnly && (
            <button
              type="button"
              className="govuk-button govuk-button--secondary"
              onClick={() => onSaveTranscriptOnly(draftNames)}
              disabled={isBusy}
            >
              Save transcript only
            </button>
          )}
          <button
            type="button"
            className="govuk-button"
            onClick={() => onSaveAndGenerate(draftNames)}
            disabled={isBusy}
          >
            {isBusy && <Loader2 className="size-4 animate-spin" />}
            Save and create new summary
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
      className="govuk-input bg-white"
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
