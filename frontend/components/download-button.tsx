'use client'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { SingleRecording } from '@/lib/client'
import { Download } from 'lucide-react'
import posthog from 'posthog-js'

export const DownloadButton = ({
  recordings,
}: {
  recordings: SingleRecording[]
}) => {
  const onClick = (recording: SingleRecording) => () => {
    posthog.capture('recording_downloaded', {
      extension: recording.extension,
      recording_id: recording.id,
    })
  }
  if (recordings.length == 1) {
    return (
      <a
        href={recordings[0].url}
        download
        role="button"
        onClick={onClick(recordings[0])}
        className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0"
      >
        <Download className="size-4" /> Download audio
      </a>
    )
  }
  return (
    <Dialog>
      <DialogTrigger asChild>
        <button className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0">
          <Download className="size-4" /> Download audio
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Download audio</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          {recordings.map((recording) => (
            <a
              key={recording.id}
              href={recording.url}
              download
              role="button"
              onClick={onClick(recording)}
              className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0"
            >
              <Download className="size-4" /> Download {recording.extension}{' '}
              file
            </a>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
