'use client'

import { DiscardConfirmDialog } from '@/components/audio/discard-dialog'
import { GenerateSummaryDialog } from '@/components/audio/generate-summary-dialog'
import { useStartTranscription } from '@/hooks/useStartTranscription'
import { getFileExtensionFromBlob } from '@/lib/getFileExtension'
import {
  RecordingDbItem,
  useRecordingDb,
} from '@/providers/transcription-db-provider'
import { useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import posthog from 'posthog-js'
import { useMemo, useState } from 'react'
import { FormProvider } from 'react-hook-form'
import { DownloadIcon, UploadIcon } from 'lucide-react'

export const OfflineRecordingRow = ({
  recording,
  selectedIds,
  onToggle,
}: {
  recording: RecordingDbItem
  selectedIds?: Set<string>
  onToggle?: (id: string, checked: boolean) => void
}) => {
  const { removeRecording } = useRecordingDb()
  const router = useRouter()
  const { form, isPending, onSubmit } = useStartTranscription(
    {
      file: recording.blob,
      recordingId: recording.recording_id,
    },
    (id) => router.push(`/new/status/${id}`)
  )
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const queryClient = useQueryClient()
  const url = useMemo(
    () => URL.createObjectURL(recording.blob),
    [recording.blob]
  )
  const label = recording.updated_at.toLocaleTimeString('en-GB', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
  return (
    <tr className="govuk-table__row govuk-!-padding-top-1 govuk-!-padding-bottom-1 relative flex items-center gap-4 border-b border-(--govuk-border-colour)">
      <td className="govuk-!-padding-0">
        <div
          className="govuk-checkboxes govuk-checkboxes--small flex"
          data-module="govuk-checkboxes"
        >
          <input
            className="govuk-checkboxes__input"
            id={`offline-${recording.recording_id}`}
            name="offline-recording"
            type="checkbox"
            value={recording.recording_id}
            checked={selectedIds?.has(recording.recording_id) ?? false}
            onChange={(e) =>
              onToggle?.(recording.recording_id, e.target.checked)
            }
          />
          <label
            className="govuk-label govuk-checkboxes__label"
            htmlFor={`offline-${recording.recording_id}`}
          >
            <span className="govuk-visually-hidden">Select {label}</span>
          </label>
        </div>
      </td>
      <td className="govuk-!-padding-0">
        <audio src={url} controls />
      </td>
      <td className="govuk-!-padding-0 min-w-26 flex-1">
        <span className="govuk-body-s govuk-!-margin-0">{label}</span>
      </td>
      <td className="govuk-!-padding-0">
        <div className="flex items-center justify-end gap-4">
          <button
            type="button"
            className="govuk-button govuk-!-margin-0 flex items-center gap-2 hover:cursor-pointer"
            onClick={() => setUploadOpen(true)}
          >
            <UploadIcon className="size-4" />
            Upload
            <span className="govuk-visually-hidden">{label}</span>
          </button>
          <a
            href={url}
            download={`audio-file.${getFileExtensionFromBlob(recording.blob)}`}
            className="govuk-button govuk-button--secondary govuk-!-margin-0 flex items-center gap-2 hover:cursor-pointer"
          >
            <DownloadIcon className="size-4" />
            Download
            <span className="govuk-visually-hidden">{label}</span>
          </a>
          <button
            type="button"
            className="govuk-link link--warning flex items-center gap-2 hover:cursor-pointer"
            onClick={() => setDeleteOpen(true)}
          >
            Delete
            <span className="govuk-visually-hidden">{label}</span>
          </button>
        </div>
      </td>
      <FormProvider {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <GenerateSummaryDialog
            open={uploadOpen}
            onOpenChange={setUploadOpen}
            title="Generate summary"
            onConfirm={form.handleSubmit(onSubmit)}
            disabled={isPending}
          />
        </form>
      </FormProvider>
      <DiscardConfirmDialog
        open={deleteOpen}
        setOpen={setDeleteOpen}
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
    </tr>
  )
}
