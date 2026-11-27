import {
  listTranscriptionKeywordsTranscriptionsTranscriptionIdKeywordsGetOptions,
  replaceTranscriptionKeywordsTranscriptionsTranscriptionIdKeywordsPutMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'

export function useTranscriptionKeywords(
  transcriptionId: string,
  enabled: boolean
) {
  const path = { transcription_id: transcriptionId }
  const options =
    listTranscriptionKeywordsTranscriptionsTranscriptionIdKeywordsGetOptions({
      path,
    })
  const query = useQuery({ ...options, enabled })
  const queryClient = useQueryClient()
  const original = useRef<string[]>(undefined)
  const [draft, setDraft] = useState<string[]>()
  const mutation = useMutation({
    ...replaceTranscriptionKeywordsTranscriptionsTranscriptionIdKeywordsPutMutation(),
    async onSuccess(data) {
      await queryClient.cancelQueries({ queryKey: options.queryKey })
      queryClient.setQueryData(options.queryKey, data)
    },
  })

  return {
    saved: query.data?.keywords,
    field: {
      keywords: draft ?? query.data?.keywords,
      onChange(keywords: string[]) {
        original.current ??= query.data?.keywords
        setDraft(keywords)
      },
      isLoading: query.isLoading,
      isError: query.isError,
      refetch: query.refetch,
      isSaving: mutation.isPending,
      saveError: mutation.isError,
    },
    reset() {
      original.current = undefined
      setDraft(undefined)
      mutation.reset()
    },
    async save() {
      if (draft && draft.join('\n') !== original.current?.join('\n')) {
        await mutation.mutateAsync({ path, body: { keywords: draft } })
        original.current = draft
      }
    },
  }
}
