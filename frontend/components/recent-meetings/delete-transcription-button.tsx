'use client'

import {
  DeleteTranscription,
  DeleteTranscriptionDialog,
} from '@/components/recent-meetings/delete-transcription-dialog'
import { useState } from 'react'

export function DeleteTranscriptionButton({
  transcription,
  title,
  disabled,
}: {
  transcription: DeleteTranscription
  title?: string
  disabled?: boolean
}) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        className={`govuk-link ${disabled ? '!text-gray-400 pointer-events-none' : 'link--warning hover:cursor-pointer'}`}
        onClick={() => setOpen(true)}
        disabled={disabled}
      >
        Delete
        <span className="govuk-visually-hidden">{title}</span>
      </button>
      <DeleteTranscriptionDialog
        open={open}
        setOpen={setOpen}
        transcription={transcription}
      />
    </>
  )
}
