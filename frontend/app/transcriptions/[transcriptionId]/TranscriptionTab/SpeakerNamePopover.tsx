'use client'

import { DialogueEntryForm } from '@/types/transcriptions'
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import posthog from 'posthog-js'
import { useCallback, useEffect, useState } from 'react'
import { useFormContext } from 'react-hook-form'

export const SpeakerNamePopover = ({
  entry,
  index,
  update,
}: {
  entry: DialogueEntryForm['entries'][0]
  index: number
  update: (index: number, etnry: DialogueEntryForm['entries'][0]) => void
}) => {
  const [open, setOpen] = useState(false)
  const { getValues } = useFormContext<DialogueEntryForm>()
  const [newName, setNewName] = useState(entry.speaker)
  const inputId = `speaker-name-${index}`
  const hintId = `speaker-name-hint-${index}`

  useEffect(() => {
    if (open) {
      setNewName(entry.speaker)
    }
  }, [open, entry.speaker])

  const handleUpdateAll = useCallback(() => {
    getValues('entries')
      .map((e, i) => ({
        ...e,
        i,
      }))
      .filter((e) => e.speaker === entry.speaker)
      .forEach(({ i, ...entry }) => {
        update(i, { ...entry, speaker: newName })
      })
    posthog.capture('speaker_name_edited_in_transcript', {
      update_type: 'all_occurances',
    })
    setOpen(false)
  }, [entry.speaker, getValues, newName, update])

  const handleUpdateSingle = useCallback(() => {
    update(index, { ...entry, speaker: newName })
    setOpen(false)
    posthog.capture('speaker_name_edited_in_transcript', {
      update_type: 'single_occurrence',
      entry_index: index,
    })
  }, [entry, index, newName, update])

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button
          type="button"
          className="govuk-link govuk-link--no-visited-state text-(--govuk-link-colour)"
        >
          Edit name
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle>
          <label
            className="govuk-label govuk-label--m govuk-!-margin-bottom-0"
            htmlFor={inputId}
          >
            Edit speaker name
          </label>
        </DialogTitle>
        <input
          className="govuk-input"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          id={inputId}
          name={inputId}
          type="text"
          aria-describedby={hintId}
        />
        <div className="govuk-button-group govuk-!-margin-top-4 govuk-!-margin-bottom-0">
          <button
            type="button"
            className="govuk-button govuk-button--secondary"
            onClick={handleUpdateSingle}
          >
            Update this occurrence
          </button>
          <button
            type="button"
            className="govuk-button"
            onClick={handleUpdateAll}
          >
            Update all occurrences
          </button>
        </div>
        <div className="govuk-button-group justify-end">
          <button
            type="button"
            className="govuk-button govuk-button--secondary"
            onClick={() => setOpen(false)}
          >
            Cancel
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
