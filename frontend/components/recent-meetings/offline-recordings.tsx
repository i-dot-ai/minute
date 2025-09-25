'use client'

import { DiscardConfirmDialog } from '@/components/audio/discard-dialog'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  RecordingDbItem,
  useRecordingDb,
} from '@/providers/transcription-db-provider'
import { CollapsibleContent } from '@radix-ui/react-collapsible'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ChevronDown,
  ChevronUp,
  Clock,
  CloudOffIcon,
  Download,
  Trash,
  Upload,
} from 'lucide-react'
import Link from 'next/link'
import posthog from 'posthog-js'
import { useMemo, useState } from 'react'

export const OfflineRecordings = () => {
  const { listRecordings } = useRecordingDb()
  const { data: dbRecordings = [] } = useQuery({
    queryKey: ['list-db-recordings'],
    queryFn: listRecordings,
  })
  const [open, setOpen] = useState(false)
  if (dbRecordings.length == 0) {
    return null
  }
  return (
    <div className="mb-4 w-full rounded-md border p-4">
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger className="flex w-full items-center justify-between">
          <h4 className="flex items-center gap-1 font-bold">
            <CloudOffIcon /> Offline recordings
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-500/20 text-xs text-blue-500">
              {dbRecordings.length}
            </div>
          </h4>
          {open ? <ChevronUp /> : <ChevronDown />}
        </CollapsibleTrigger>
        <CollapsibleContent>
          <p className="text-muted-foreground mt-2 mb-4 text-left text-sm">
            These are recording backups which are stored in this browser. We
            strongly recommend you delete or upload these so they are securely
            and reliably stored in the cloud.
          </p>
          <ul className="flex flex-col gap-2">
            {dbRecordings
              .sort((a, b) => b.updated_at.valueOf() - a.updated_at.valueOf())
              .map((r) => (
                <OfflineRecording recording={r} key={r.recording_id} />
              ))}
          </ul>
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}

const OfflineRecording = ({ recording }: { recording: RecordingDbItem }) => {
  const { removeRecording } = useRecordingDb()
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const url = useMemo(
    () => URL.createObjectURL(recording.blob),
    [recording.blob]
  )
  return (
    <li className="flex w-full flex-col gap-2 rounded border bg-slate-50 p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="text-muted-foreground flex items-center gap-1 text-sm">
          <Clock size="0.8rem" /> {recording.updated_at.toDateString()} at{' '}
          {recording.updated_at.toLocaleTimeString()}
        </div>
        <div className="flex items-center gap-2">
          <Button asChild>
            <Link href={`/recordings/${recording.recording_id}`}>
              <Upload /> Upload recording
            </Link>
          </Button>
          <Button
            variant="outline"
            className="border-red-500/20 text-red-700"
            onClick={() => setOpen(true)}
          >
            <Trash /> Delete recording
          </Button>
        </div>
      </div>
      <audio src={url} controls className="w-full" />
      <div className="flex justify-end bg-gray-50 dark:bg-gray-900">
        <a
          href={url}
          download={`audio-recording-${recording.updated_at.toISOString()}.webm`}
          className="flex items-center gap-1 text-sm text-blue-600 hover:underline dark:text-blue-400"
        >
          <Download size="1rem" />
          Save to Computer
        </a>
      </div>
      <DiscardConfirmDialog
        open={open}
        setOpen={setOpen}
        onClickConfirm={() => {
          removeRecording(recording.recording_id)
          queryClient.invalidateQueries({
            queryKey: ['list-db-recordings'],
          })
          posthog.capture('offline_recording_deleted', {
            size: recording.blob.size,
          })
        }}
      />
    </li>
  )
}
