'use client'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { TranscriptionMetadata } from '@/lib/client'
import {
  listTranscriptionsTranscriptionsGetQueryKey,
  saveTranscriptionTranscriptionsTranscriptionIdPatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader, Save } from 'lucide-react'
import posthog from 'posthog-js'
import { Dispatch, SetStateAction } from 'react'
import { useForm } from 'react-hook-form'

export const RenameDialog = ({
  open,
  setOpen,
  transcription,
}: {
  open: boolean
  setOpen: Dispatch<SetStateAction<boolean>>
  transcription: TranscriptionMetadata
}) => {
  const queryClient = useQueryClient()
  const { mutate: saveTranscription, isPending } = useMutation({
    ...saveTranscriptionTranscriptionsTranscriptionIdPatchMutation(),
    onSuccess() {
      queryClient.invalidateQueries({
        queryKey: listTranscriptionsTranscriptionsGetQueryKey(),
      })
      posthog.capture('edited_transcript_title', {
        transcriptionId: transcription.id,
      })
      setOpen(false)
    },
  })
  const form = useForm<{ title: string | undefined }>({
    defaultValues: { title: transcription.title ?? undefined },
  })
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <form
          onSubmit={form.handleSubmit(({ title }) => {
            saveTranscription({
              path: { transcription_id: transcription.id },
              body: { title },
            })
          })}
        >
          <DialogHeader>
            <DialogTitle>Rename meeting</DialogTitle>
            <DialogClose />
          </DialogHeader>
          <Input
            {...form.register('title')}
            className="mb-4"
            placeholder="Add title"
          />
          <DialogFooter>
            <DialogClose asChild>
              <Button
                variant="secondary"
                type="button"
                className="hover:bg-slate-200"
              >
                Cancel
              </Button>
            </DialogClose>
            <Button className="active:bg-yellow-400" type="submit">
              {isPending ? (
                <Loader />
              ) : (
                <>
                  <Save /> Save
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
