'use client'

import {
  formatMeetingTime,
  MeetingTimeField,
  toApiMeetingDatetime,
  toMeetingTime,
} from '@/components/audio/meeting-time-field'
import { TranscriptionForm } from '@/components/audio/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  getTranscriptionTranscriptionsTranscriptionIdGetQueryKey,
  listTranscriptionsTranscriptionsGetQueryKey,
  saveTranscriptionTranscriptionsTranscriptionIdPatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Ellipsis } from 'lucide-react'
import posthog from 'posthog-js'
import { useEffect, useState } from 'react'
import { FormProvider, useForm } from 'react-hook-form'

type MeetingWithTime = { id: string; meeting_datetime: string }

// Shown above the summary rather than written into it, so it stays right when
// the meeting time is changed.
export const MeetingTimeLine = ({
  transcription,
}: {
  transcription: MeetingWithTime
}) => (
  <p className="govuk-body govuk-hint govuk-!-margin-bottom-4">
    {formatMeetingTime(new Date(transcription.meeting_datetime))}
  </p>
)

// The "⋯" menu next to a meeting's title.
export const MeetingOptionsMenu = ({
  transcription,
}: {
  transcription: MeetingWithTime
}) => {
  const [menuOpen, setMenuOpen] = useState(false)
  const [changeOpen, setChangeOpen] = useState(false)

  return (
    <>
      <Popover open={menuOpen} onOpenChange={setMenuOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0 shrink-0"
          >
            <Ellipsis className="size-4" aria-hidden />
            <span className="govuk-visually-hidden">Meeting options</span>
          </button>
        </PopoverTrigger>
        <PopoverContent align="end" className="w-auto rounded-none p-2">
          <ul>
            <li>
              <button
                type="button"
                className="govuk-link govuk-link--no-underline govuk-!-font-size-19 w-full px-3 py-2 text-left hover:cursor-pointer"
                onClick={() => {
                  setMenuOpen(false)
                  setChangeOpen(true)
                }}
              >
                Change meeting date
              </button>
            </li>
          </ul>
        </PopoverContent>
      </Popover>
      <ChangeMeetingTimeDialog
        transcription={transcription}
        open={changeOpen}
        onOpenChange={setChangeOpen}
      />
    </>
  )
}

const ChangeMeetingTimeDialog = ({
  transcription,
  open,
  onOpenChange,
}: {
  transcription: MeetingWithTime
  open: boolean
  onOpenChange: (open: boolean) => void
}) => {
  const queryClient = useQueryClient()
  const [errorText, setErrorText] = useState<string>()
  const form = useForm<TranscriptionForm>()

  useEffect(() => {
    if (open) {
      setErrorText(undefined)
      form.reset({
        meeting_datetime: toMeetingTime(
          new Date(transcription.meeting_datetime)
        ),
      })
    }
  }, [form, open, transcription.meeting_datetime])

  const { mutate: save, isPending } = useMutation({
    ...saveTranscriptionTranscriptionsTranscriptionIdPatchMutation(),
    onSuccess() {
      queryClient.invalidateQueries({
        queryKey: listTranscriptionsTranscriptionsGetQueryKey(),
      })
      queryClient.invalidateQueries({
        queryKey: getTranscriptionTranscriptionsTranscriptionIdGetQueryKey({
          path: { transcription_id: transcription.id },
        }),
      })
      posthog.capture('changed_meeting_date', {
        transcriptionId: transcription.id,
      })
      onOpenChange(false)
    },
    onError() {
      setErrorText('Could not change the meeting date. Please try again.')
    },
  })

  const onSubmit = ({ meeting_datetime }: TranscriptionForm) => {
    setErrorText(undefined)
    save({
      path: { transcription_id: transcription.id },
      body: { meeting_datetime: toApiMeetingDatetime(meeting_datetime) },
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent showCloseButton={false}>
        <FormProvider {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <DialogHeader>
              <DialogTitle className="govuk-heading-m">
                Change the meeting date
              </DialogTitle>
            </DialogHeader>
            <MeetingTimeField startEditing />
            {errorText && (
              <Alert variant="destructive">
                <AlertDescription>{errorText}</AlertDescription>
              </Alert>
            )}
            <DialogFooter className="govuk-button-group sm:ml-auto sm:justify-end">
              <button
                type="button"
                className="govuk-button govuk-button--secondary"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="govuk-button"
                disabled={isPending}
              >
                Save
              </button>
            </DialogFooter>
          </form>
        </FormProvider>
      </DialogContent>
    </Dialog>
  )
}
