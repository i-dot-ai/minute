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
import { MinuteListItem } from '@/lib/client'
import {
  deleteMinuteMinutesMinuteIdDeleteMutation,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import posthog from 'posthog-js'
import { useState } from 'react'

export function DeleteMinuteButton({
  minute,
  transcriptionId,
  disabled,
}: {
  minute: MinuteListItem
  transcriptionId: string
  disabled?: boolean
}) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const router = useRouter()
  const { mutate: deleteMinute, isPending } = useMutation({
    ...deleteMinuteMinutesMinuteIdDeleteMutation(),
    onSuccess() {
      queryClient.invalidateQueries({
        queryKey:
          listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetQueryKey(
            {
              path: { transcription_id: transcriptionId },
            }
          ),
      })
      posthog.capture('deleted_minute', { minuteId: minute.id })
      setOpen(false)
      router.push(`/transcriptions/${transcriptionId}`)
    },
  })

  return (
    <>
      <button
        type="button"
        className="govuk-link link--warning govuk-!-font-size-16"
        onClick={() => setOpen(true)}
        disabled={disabled}
      >
        Delete summary
      </button>
      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="govuk-heading-l">
              Are you sure you want to delete this summary?
            </AlertDialogTitle>
            <AlertDialogDescription className="govuk-body">
              This will permanently delete this summary and its version history.
              The transcription will not be deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <p className="govuk-body govuk-!-font-weight-bold">
            {minute.template_name}
          </p>
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
              onClick={() => deleteMinute({ path: { minute_id: minute.id! } })}
            >
              Delete summary
            </button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
