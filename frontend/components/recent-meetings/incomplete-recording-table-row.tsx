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

export const IncompleteRecordingTableRow = ({
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
  const date = recording.updated_at.toLocaleString('en-GB', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <tr className="govuk-table__row bg-[#f4d7d7] has-[:checked]:bg-[#f4f8fb]">
      <td className="govuk-table__cell govuk-!-padding-left-1">
        <div
          className="govuk-checkboxes govuk-checkboxes--small govuk-checkboxes--subtle relative flex"
          data-module="govuk-checkboxes"
        >
          <input
            className="govuk-checkboxes__input"
            id={`incomplete-recording-${recording.recording_id}`}
            name="incomplete-recording"
            type="checkbox"
            value={recording.recording_id}
            checked={selectedIds?.has(recording.recording_id) ?? false}
            onChange={(e) =>
              onToggle?.(recording.recording_id, e.target.checked)
            }
          />
          <label
            className="govuk-label govuk-checkboxes__label govuk-!-padding-0 before:!bg-white"
            htmlFor={`incomplete-recording-${recording.recording_id}`}
          >
            <span className="govuk-visually-hidden">
              Select incomplete recording {date}
            </span>
          </label>
        </div>
      </td>
      <td className="govuk-table__cell govuk-!-padding-right-4 w-full">
        <div className="flex items-center justify-between gap-2">
          <span>Incomplete recording</span>
          <audio src={url} controls className="max-h-10 w-52" />
        </div>
      </td>
      <td className="govuk-table__cell whitespace-nowrap">
        <span className="govuk-body-s govuk-!-margin-0">{date}</span>
      </td>
      <td className="govuk-table__cell govuk-!-padding-left-4 govuk-!-padding-right-4 whitespace-nowrap">
        <strong className="govuk-tag govuk-tag--yellow govuk-!-margin-right-1 govuk-!-padding-left-1 govuk-!-font-size-16">
          Not uploaded
        </strong>
      </td>
      <td className="govuk-table__cell whitespace-nowrap">
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="govuk-link govuk-link--no-underline govuk-!-font-size-16 text-(--govuk-link-colour)"
            onClick={() => setUploadOpen(true)}
          >
            Upload
            <span className="govuk-visually-hidden">
              incomplete recording {date}
            </span>
          </button>
          <a
            href={url}
            download={`audio-file.${getFileExtensionFromBlob(recording.blob)}`}
            className="govuk-link govuk-link--no-underline govuk-!-font-size-16 text-(--govuk-link-colour)"
          >
            Download
            <span className="govuk-visually-hidden">
              incomplete recording {date}
            </span>
          </a>
          <button
            type="button"
            className="govuk-link govuk-link--no-underline link--warning govuk-!-font-size-16"
            onClick={() => setDeleteOpen(true)}
          >
            Delete
            <span className="govuk-visually-hidden">
              incomplete recording {date}
            </span>
          </button>
        </div>
      </td>
      <FormProvider {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <GenerateSummaryDialog
            open={uploadOpen}
            onOpenChange={setUploadOpen}
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
