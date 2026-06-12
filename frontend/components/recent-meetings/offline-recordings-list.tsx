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

const OfflineRecordingItem = ({ recording }: { recording: RecordingDbItem }) => {
  const { removeRecording } = useRecordingDb()
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const url = useMemo(
    () => URL.createObjectURL(recording.blob),
    [recording.blob]
  )
  return (
    <li className="transcriptions__list-item govuk-!-padding-top-3">
      <h3 className="govuk-heading-s govuk-!-margin-bottom-1">
        {recording.updated_at.toDateString()} at{' '}
        {recording.updated_at.toLocaleTimeString()}
      </h3>
      <audio src={url} controls className="w-full" />
      <ul className="govuk-button-group">
        <li>
          <Link
            href={`/recordings/${recording.recording_id}`}
            className="govuk-link"
          >
            Upload
            <span className="govuk-visually-hidden">
              {' '}
              recording recorded on {recording.updated_at.toDateString()}{' '}
              at {recording.updated_at.toLocaleTimeString()}
            </span>
          </Link>
        </li>
        <li>
          <a
            href={url}
            download={`audio-recording-${recording.updated_at.toISOString()}.webm`}
            className="govuk-link"
          >
            Save to device
            <span className="govuk-visually-hidden">
              {' '}
              recording recorded on {recording.updated_at.toDateString()}{' '}
              at {recording.updated_at.toLocaleTimeString()}
            </span>
          </a>
        </li>
        <li>
          <button
            type="button"
            className="govuk-link text-red-700"
            onClick={() => setOpen(true)}
          >
            Delete
            <span className="govuk-visually-hidden">
              {' '}
              recording recorded on {recording.updated_at.toDateString()}{' '}
              at {recording.updated_at.toLocaleTimeString()}
            </span>
          </button>
        </li>
      </ul>
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
    </li >
  )
}
