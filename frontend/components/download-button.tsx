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
      <Button asChild variant="link" onClick={onClick(recordings[0])}>
        <a
          href={recordings[0].url}
          download
          className="text-sm text-blue-600 hover:underline dark:text-blue-400"
        >
          <Download /> Download
        </a>
      </Button>
    )
  }
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="link">
          <Download /> Download
        </Button>
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
