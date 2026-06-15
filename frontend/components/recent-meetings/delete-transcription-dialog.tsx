'use client'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import { JobStatus } from '@/lib/client'
import {
  deleteTranscriptionTranscriptionsTranscriptionIdDeleteMutation,
  listTranscriptionsTranscriptionsGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import posthog from 'posthog-js'
import { Dispatch, SetStateAction } from 'react'

export type DeleteTranscription = {
  id: string
  title?: string | null
  status: JobStatus
  created_datetime: string
}

export const DeleteTranscriptionDialog = ({
  open,
  setOpen,
  transcription,
}: {
  open: boolean
  setOpen: Dispatch<SetStateAction<boolean>>
  transcription: DeleteTranscription
}) => {
  const date = new Date(transcription.created_datetime)
  const queryClient = useQueryClient()
  const router = useRouter()
  const { mutate: deleteTranscription, isPending } = useMutation({
    ...deleteTranscriptionTranscriptionsTranscriptionIdDeleteMutation(),
    onSuccess() {
      queryClient.invalidateQueries({
        queryKey: listTranscriptionsTranscriptionsGetQueryKey(),
      })
      posthog.capture('deleted_transcript', {
        transcriptionId: transcription.id,
        transcriptionDate: transcription.created_datetime,
      })
      setOpen(false)
      router.push('/transcriptions')
    },
  })

  const title =
    transcription.title ||
    (['awaiting_start', 'in_progress'].includes(transcription.status)
      ? 'Generating title'
      : 'No title')

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogTitle className="govuk-heading-l">
          Are you sure you want to delete this transcription?
        </DialogTitle>
        <DialogDescription className="govuk-body">
          This will permanently delete the transcription and cannot be undone.
        </DialogDescription>
        <p className="govuk-body govuk-!-font-weight-bold">{title}</p>
        <p className="govuk-body-s">
          {date.toLocaleDateString('en-GB', {
            day: 'numeric',
            month: 'long',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
        <div className="govuk-button-group">
          <button
            type="button"
            className="govuk-button govuk-button--secondary"
            disabled={isPending}
            onClick={() => setOpen(false)}
          >
            Cancel
          </button>
          <button
            type="button"
            className="govuk-button govuk-button--warning"
            disabled={isPending}
            onClick={() =>
              deleteTranscription({
                path: { transcription_id: transcription.id },
              })
            }
          >
            {isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Deleting
              </>
            ) : (
              'Delete transcription'
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
