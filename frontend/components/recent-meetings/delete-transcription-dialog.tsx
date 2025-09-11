'use client'

import { TranscriptionCard } from '@/components/recent-meetings/transcription-card'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { TranscriptionMetadata } from '@/lib/client'
import {
  deleteTranscriptionTranscriptionsTranscriptionIdDeleteMutation,
  listTranscriptionsTranscriptionsGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader, Trash } from 'lucide-react'
import posthog from 'posthog-js'
import { Dispatch, SetStateAction } from 'react'

export const DeleteDialog = ({
  open,
  setOpen,
  transcription,
}: {
  open: boolean
  setOpen: Dispatch<SetStateAction<boolean>>
  transcription: TranscriptionMetadata
}) => {
  const queryClient = useQueryClient()
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
    },
  })
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Are you sure?</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete this transcription?
          </DialogDescription>
          <TranscriptionCard
            transcription={transcription}
            className="rounded-md border p-2 text-sm"
          />
          <DialogClose />
        </DialogHeader>
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
          <Button
            variant="destructive"
            className="hover:bg-red-800 active:bg-yellow-400"
            onClick={() =>
              deleteTranscription({
                path: { transcription_id: transcription.id },
              })
            }
          >
            {isPending ? (
              <Loader />
            ) : (
              <>
                <Trash /> Yes, delete
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
