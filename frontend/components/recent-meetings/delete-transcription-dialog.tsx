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
import { JobStatus } from '@/lib/client'
import {
  deleteTranscriptionTranscriptionsTranscriptionIdDeleteMutation,
  listTranscriptionsTranscriptionsGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { usePathname, useRouter } from 'next/navigation'
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
  const pathname = usePathname()
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
      if (pathname.startsWith('/transcriptions/')) {
        router.push('/transcriptions')
      }
    },
  })

  const title =
    transcription.title ||
    (['awaiting_start', 'in_progress'].includes(transcription.status)
      ? 'Generating title'
      : 'No title')

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="govuk-heading-l">
            Are you sure you want to delete this transcription?
          </AlertDialogTitle>
          <AlertDialogDescription className="govuk-body">
            This will permanently delete the transcription and cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
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
        <AlertDialogFooter className="govuk-button-group sm:justify-start">
          <AlertDialogCancel asChild>
            <button
              type="button"
              className="govuk-button govuk-button--secondary"
              disabled={isPending}
            >
              Cancel
            </button>
          </AlertDialogCancel>
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
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
