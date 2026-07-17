'use client'

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { listTranscriptionsTranscriptionsGetQueryKey } from '@/lib/client/@tanstack/react-query.gen'
import { deleteTranscriptionTranscriptionsTranscriptionIdDelete } from '@/lib/client/sdk.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import posthog from 'posthog-js'
import { Dispatch, SetStateAction } from 'react'

export const DeleteTranscriptionsDialog = ({
  open,
  setOpen,
  transcriptionIds,
  onDeleted,
}: {
  open: boolean
  setOpen: Dispatch<SetStateAction<boolean>>
  transcriptionIds: string[]
  onDeleted: () => void
}) => {
  const queryClient = useQueryClient()
  const count = transcriptionIds.length
  const { mutate: deleteTranscriptions, isPending } = useMutation({
    mutationFn: async (ids: string[]) => {
      await Promise.all(
        ids.map((id) =>
          deleteTranscriptionTranscriptionsTranscriptionIdDelete({
            path: { transcription_id: id },
          })
        )
      )
    },
    onSuccess: (_, ids) => {
      queryClient.invalidateQueries({
        queryKey: listTranscriptionsTranscriptionsGetQueryKey(),
      })
      posthog.capture('deleted_transcripts_bulk', { count: ids.length })
      setOpen(false)
      onDeleted()
    },
  })

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="govuk-heading-l">
            Are you sure you want to delete {count}{' '}
            {count === 1 ? 'transcription' : 'transcriptions'}?
          </AlertDialogTitle>
          <AlertDialogDescription className="govuk-body">
            This will permanently delete the selected transcriptions and cannot
            be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="govuk-button-group sm:justify-end">
          <AlertDialogCancel asChild>
            <button
              type="button"
              className="govuk-button govuk-button--secondary !no-underline"
              disabled={isPending}
            >
              Cancel
            </button>
          </AlertDialogCancel>
          <button
            type="button"
            className="govuk-button govuk-button--warning"
            disabled={isPending}
            onClick={() => deleteTranscriptions(transcriptionIds)}
          >
            Delete {count} selected
          </button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
