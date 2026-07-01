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
  title,
}: {
  transcription: RenameTranscription
  className?: string
  title?: string
}) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        data-module="govuk-button"
        className={className ?? 'govuk-link text-(--govuk-link-colour) govuk-!-margin-bottom-0 hover:cursor-pointer'}
        onClick={() => setOpen(true)}
      >
        <PencilIcon className="size-4" />
        <span className="govuk-visually-hidden">Rename {title}</span>
      </button>
      <RenameTranscriptionDialog
        open={open}
        setOpen={setOpen}
        transcription={transcription}
      />
    </>
  )
}
