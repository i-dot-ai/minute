'use client'

import { Dialog, DialogContent } from '@/components/ui/dialog'
import { JobStatus } from '@/lib/client'
import {
  getTranscriptionTranscriptionsTranscriptionIdGetQueryKey,
  listTranscriptionsTranscriptionsGetQueryKey,
  saveTranscriptionTranscriptionsTranscriptionIdPatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import posthog from 'posthog-js'
import { Dispatch, SetStateAction, useEffect } from 'react'
import { useForm } from 'react-hook-form'

export type RenameTranscription = {
  id: string
  title?: string | null
  status: JobStatus
}

export function getTranscriptionDisplayTitle(
  title: string | null | undefined,
  status: JobStatus
) {
  return (
    title ||
    (['awaiting_start', 'in_progress'].includes(status)
      ? 'Generating title'
      : 'No title')
  )
}

export const RenameTranscriptionDialog = ({
  open,
  setOpen,
  transcription,
}: {
  open: boolean
  setOpen: Dispatch<SetStateAction<boolean>>
  transcription: RenameTranscription
}) => {
  const queryClient = useQueryClient()
  const form = useForm<{ title: string }>({
    defaultValues: { title: transcription.title ?? '' },
  })

  useEffect(() => {
    if (open) {
      form.reset({ title: transcription.title ?? '' })
    }
  }, [form, open, transcription.title])

  const { mutate: saveTranscription, isPending } = useMutation({
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
      posthog.capture('edited_transcript_title', {
        transcriptionId: transcription.id,
      })
      setOpen(false)
    },
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <form
          onSubmit={form.handleSubmit(({ title }) => {
            saveTranscription({
              path: { transcription_id: transcription.id },
              body: { title: title.trim() || null },
            })
          })}
        >
          <h1 className="govuk-heading-l">Rename transcription</h1>
          <div className="govuk-form-group">
            <label className="govuk-label" htmlFor="transcription-title">
              Title
            </label>
            <input
              className="govuk-input"
              id="transcription-title"
              type="text"
              placeholder="Add title"
              {...form.register('title')}
            />
          </div>
          <div className="govuk-button-group">
            <button
              type="submit"
              className="govuk-button"
              disabled={isPending}
            >
              {isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" /> Saving
                </>
              ) : (
                'Save title'
              )}
            </button>
            <button
              type="button"
              className="govuk-button govuk-button--secondary"
              disabled={isPending}
              onClick={() => setOpen(false)}
            >
              Cancel
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
