'use client'

import CopyButton from '@/components/ui/copy-button'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { SingleRecording } from '@/lib/client'
import { Download } from 'lucide-react'
import posthog from 'posthog-js'
import { useState } from 'react'

export const ExportTranscriptDialog = ({
  transcriptionString,
  recordings = [],
}: {
  transcriptionString: string
  recordings?: SingleRecording[]
}) => {
  const [open, setOpen] = useState(false)

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <button
        type="button"
        className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0"
        onClick={() => setOpen(true)}
      >
        <Download className="size-4" />
        Export
      </button>
      <DialogContent>
        <DialogTitle className="govuk-heading-l">Export transcript</DialogTitle>
        <p className="govuk-body">Copy transcript</p>
        <div className="govuk-button-group">
          <CopyButton
            textToCopy={transcriptionString}
            posthogEvent="transcript_content_copied"
            label="Copy transcript"
            onCopied={() => setOpen(false)}
          />
        </div>
        <p className="govuk-body">Download audio:</p>
        <div className="govuk-button-group">
          {recordings.map((recording) => (
            <a
              key={recording.id}
              href={recording.url}
              download
              role="button"
              className="govuk-button govuk-button--secondary"
              onClick={() => {
                posthog.capture('recording_downloaded', {
                  extension: recording.extension,
                  recording_id: recording.id,
                })
                setOpen(false)
              }}
            >
              <Download className="size-4" /> Download{' '}
              {recordings.length > 1 ? `${recording.extension} file` : 'audio'}
            </a>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
