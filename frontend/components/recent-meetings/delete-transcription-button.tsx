'use client'

import {
  DeleteTranscription,
  DeleteTranscriptionDialog,
} from '@/components/recent-meetings/delete-transcription-dialog'
import { useState } from 'react'

export function DeleteTranscriptionButton({
  transcription,
  className,
}: {
  transcription: DeleteTranscription
  className?: string
}) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        className={className ?? 'govuk-link link--warning'}
        onClick={() => setOpen(true)}
      >
        Delete
      </button>
      <DeleteTranscriptionDialog
        open={open}
        setOpen={setOpen}
        transcription={transcription}
      />
    </>
  )
}
