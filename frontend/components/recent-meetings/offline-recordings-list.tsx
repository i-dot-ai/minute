'use client'

import { DiscardConfirmDialog } from '@/components/audio/discard-dialog'
import {
  RecordingDbItem,
  useRecordingDb,
} from '@/providers/transcription-db-provider'
import { useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import posthog from 'posthog-js'
import { useMemo, useState } from 'react'
import { DownloadIcon, TrashIcon, UploadIcon } from 'lucide-react'

export function OfflineRecordingsList({
  recordings,
}: {
  recordings: RecordingDbItem[]
}) {
  return (
    <ul className="govuk-list">
      {recordings.map((recording) => (
        <OfflineRecordingItem
          recording={recording}
          key={recording.recording_id}
        />
      ))}
    </ul>
  )
}

const OfflineRecordingItem = ({
  recording,
}: {
  recording: RecordingDbItem
}) => {
  const { removeRecording } = useRecordingDb()
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const url = useMemo(
    () => URL.createObjectURL(recording.blob),
    [recording.blob]
  )
  return (
    <li className="border-t border-(--govuk-border-colour)">
      <div className="flex items-center justify-between hover:bg-[#f4f8fb]">
        <audio src={url} controls className="govuk-!-margin-right-2 govuk-!-margin-top-1" />
        <Link
          href={`/recordings/${recording.recording_id}`}
          className="govuk-link govuk-link--no-visited-state govuk-link--no-underline flex-1 flex"
          role="button"
        >
          <h3 className="govuk-body-s govuk-!-margin-bottom-0 flex-1">
            {recording.updated_at.toLocaleTimeString('en-GB', {
              day: 'numeric',
              month: 'short',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </h3>
        </Link>
        <button
          type="button"
          className="govuk-link link--warning flex items-center gap-2 hover:cursor-pointer"
          onClick={() => setOpen(true)}
        >
          <TrashIcon className="size-4" />
          Delete
          <span className="govuk-visually-hidden">
            {' '}
            recording recorded on {recording.updated_at.toDateString()} at{' '}
            {recording.updated_at.toLocaleTimeString()}
          </span>
        </button>
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
