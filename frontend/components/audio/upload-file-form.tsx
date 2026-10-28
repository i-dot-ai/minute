'use client'

import { TranscriptionForm } from '@/components/audio/types'
import { useStartTranscription } from '@/hooks/useStartTranscription'
import { Template } from '@/types/templates'
import { useEffect, useRef } from 'react'
import { RecordingFinishedState } from './recording-finished-state'

export function UploadFileForm({
  file,
  template,
  agenda,
  language,
  onDiscard,
  onStarted,
}: {
  file: File
  template: Template
  agenda?: string
  language: TranscriptionForm['language']
  onDiscard?: () => void
  onStarted?: (transcriptionId: string) => void
}) {
  const { isError, onSubmit } = useStartTranscription(
    { file, template, agenda, language },
    onStarted
  )

  // File, language, template and agenda were chosen on the home page, so submit
  // straight away. One-shot guard so Strict Mode's double-mount (dev) can't
  // create two transcriptions.
  const hasSubmitted = useRef(false)
  useEffect(() => {
    if (hasSubmitted.current) return
    hasSubmitted.current = true
    onSubmit({ file, template, agenda, language })
  }, [onSubmit, file, template, agenda, language])

  if (isError) {
    return (
      <div className="govuk-!-margin-top-4">
        <p className="govuk-body">
          Something went wrong starting your summary. Please try again.
        </p>
        <button type="button" onClick={onDiscard} className="govuk-button">
          Start again
        </button>
      </div>
    )
  }

  return <RecordingFinishedState />
}
