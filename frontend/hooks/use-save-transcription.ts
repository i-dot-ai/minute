import { DialogueEntry } from '@/lib/client'
import {
  getTranscriptionTranscriptionsTranscriptionIdGetQueryKey,
  saveTranscriptionTranscriptionsTranscriptionIdPatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'

export const useSaveTranscription = (transcription_id: string) => {
  const { mutateAsync } = useMutation({
    ...saveTranscriptionTranscriptionsTranscriptionIdPatchMutation(),
  })
  const queryClient = useQueryClient()
  const saveTranscription = useCallback(
    async (data: { entries: DialogueEntry[] }) => {
      await mutateAsync(
        {
          path: { transcription_id },
          body: { dialogue_entries: data.entries },
        },
        {
          onSuccess() {
            queryClient.invalidateQueries({
              queryKey:
                getTranscriptionTranscriptionsTranscriptionIdGetQueryKey({
                  path: { transcription_id },
                }),
            })
          },
        }
      )
    },
    [queryClient, mutateAsync, transcription_id]
  )
  return { saveTranscription }
}
