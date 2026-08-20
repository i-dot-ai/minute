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
        id="tour-delete-summary"
      >
        Delete summary
      </button>
      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="govuk-heading-l">
              Delete this summary?
            </AlertDialogTitle>
          </AlertDialogHeader>
          <AlertDialogDescription>
            <p className="govuk-body">
              <span className="govuk-!-font-weight-bold">
                {minute.template_name}
              </span>{' '}
              -{' '}
              {new Date(minute.updated_datetime).toLocaleDateString('en-GB', {
                day: 'numeric',
                month: 'short',
                year: 'numeric',
              })}
            </p>
            <p className="govuk-body">
              Only this summary is removed. The recording, its transcript and
              any other summaries stay.
            </p>
            <p className="govuk-body">This cannot be undone.</p>
          </AlertDialogDescription>

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
