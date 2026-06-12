'use client'

import {
  RenameTranscription,
  RenameTranscriptionDialog,
} from '@/components/recent-meetings/rename-transcription-dialog'
import { PencilIcon } from 'lucide-react'
import { useState } from 'react'

export function RenameTranscriptionButton({
  transcription,
  className,
}: {
  transcription: RenameTranscription
  className?: string
}) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        data-module="govuk-button"
        className={className ?? 'govuk-button govuk-button--secondary'}
        onClick={() => setOpen(true)}
      >
        <PencilIcon className="size-4" /> Rename
      </button>
      <RenameTranscriptionDialog
        open={open}
        setOpen={setOpen}
        transcription={transcription}
      />
    </>
  )
}
