'use client'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { SingleRecording } from '@/lib/client'
import { Download } from 'lucide-react'
import posthog from 'posthog-js'

export const DownloadButton = ({
  recordings,
  inverse = false,
}: {
  recordings: SingleRecording[]
  inverse?: boolean
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
        className={`govuk-button ${inverse ? 'govuk-button--inverse' : 'govuk-button--secondary'}`}
      >
        <Download className="size-4" /> Download
      </a>
    )
  }
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          className={`govuk-button ${inverse ? 'govuk-button--inverse' : 'govuk-button--secondary'}`}
        >
          <Download className="size-4" /> Download
        </button>
      </PopoverTrigger>
      <PopoverContent>
        {recordings.map((recording) => (
          <Button
            asChild
            variant="link"
            key={recording.id}
            onClick={onClick(recording)}
          >
            <a
              href={recording.url}
              download
              className="text-sm text-blue-600 hover:underline dark:text-blue-400"
            >
              <Download /> Download {recording.extension} File
            </a>
          </Button>
        ))}
      </PopoverContent>
    </Popover>
  )
}
