'use client'

import {
  DeleteTranscription,
  DeleteTranscriptionDialog,
} from '@/components/recent-meetings/delete-transcription-dialog'
import { useState } from 'react'
import { TrashIcon } from 'lucide-react'

export function DeleteTranscriptionButton({
  transcription,
  className,
  title,
}: {
  transcription: DeleteTranscription
  className?: string
  title?: string
}) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        className={className ?? 'govuk-link link--warning hover:cursor-pointer'}
        onClick={() => setOpen(true)}
      >
        <TrashIcon className="size-4" />
        <span className="govuk-visually-hidden">Delete {title}</span>
      </button>
      <DeleteTranscriptionDialog
        open={open}
        setOpen={setOpen}
        transcription={transcription}
      />
    </>
  )
}
