'use client'

import { useStartTranscription } from '@/hooks/useStartTranscription'
import { Template } from '@/types/templates'
import { useEffect, useRef } from 'react'
import { MeetingTime } from './meeting-time-field'
import { RecordingFinishedState } from './recording-finished-state'

export function UploadFileForm({
  file,
  template,
  agenda,
  meetingTime,
  orgId,
  onDiscard,
  onStarted,
}: {
  file: File
  template: Template
  agenda?: string
  meetingTime?: MeetingTime
  orgId?: string
  onDiscard?: () => void
  onStarted?: (transcriptionId: string) => void
}) {
  const { isError, onSubmit } = useStartTranscription(
    { file, template, agenda, meeting_datetime: meetingTime, orgId },
    onStarted
  )

  // File, template, agenda and meeting time were all chosen on the home page, so submit
  // straight away. One-shot guard so Strict Mode's double-mount (dev) can't
  // create two transcriptions.
  const hasSubmitted = useRef(false)
  useEffect(() => {
    if (hasSubmitted.current) return
    hasSubmitted.current = true
    onSubmit({ file, template, agenda, meeting_datetime: meetingTime, orgId })
  }, [onSubmit, file, template, agenda, meetingTime, orgId])

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
