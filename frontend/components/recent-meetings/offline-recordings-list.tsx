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
    <li className="transcriptions__list-item govuk-!-padding-top-3 govuk-!-padding-bottom-3">
      <div className="flex justify-between">
        <h3 className="govuk-heading-s govuk-!-margin-bottom-1">
          {recording.updated_at.toDateString()} at{' '}
          {recording.updated_at.toLocaleTimeString()}
        </h3>
        <div className="govuk-button-group">
          <Link
            href={`/recordings/${recording.recording_id}`}
            className="govuk-button govuk-button--secondary"
            role="button"
          >
            Upload
            <span className="govuk-visually-hidden">
              {' '}
              recording recorded on {recording.updated_at.toDateString()} at{' '}
              {recording.updated_at.toLocaleTimeString()}
            </span>
          </Link>
          <a
            href={url}
            download={`audio-recording-${recording.updated_at.toISOString()}.webm`}
            className="govuk-button govuk-button--secondary"
            role="button"
          >
            Save to device
            <span className="govuk-visually-hidden">
              {' '}
              recording recorded on {recording.updated_at.toDateString()} at{' '}
              {recording.updated_at.toLocaleTimeString()}
            </span>
          </a>
          <button
            type="button"
            className="govuk-link text-red-700"
            onClick={() => setOpen(true)}
          >
            Delete
            <span className="govuk-visually-hidden">
              {' '}
              recording recorded on {recording.updated_at.toDateString()} at{' '}
              {recording.updated_at.toLocaleTimeString()}
            </span>
          </button>
        </div>
      </div>
      <audio src={url} controls className="w-full" />
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
