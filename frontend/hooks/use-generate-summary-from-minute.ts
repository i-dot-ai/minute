import { useDefaultTemplate } from '@/hooks/useDefaultTemplate'
import { MinuteListItem } from '@/lib/client'
import {
  createMinuteTranscriptionTranscriptionIdMinutesPostMutation,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import posthog from 'posthog-js'
import { useCallback } from 'react'

/**
 * Generates a new summary reusing the template (and agenda) of an existing
 * minute via `source_minute_id`. When no source minute exists (e.g. all
 * summaries were deleted) it falls back to the user's default template, or
 * "General" if none is set.
 */
export const useGenerateSummaryFromMinute = (transcriptionId: string) => {
  const queryClient = useQueryClient()
  const defaultTemplate = useDefaultTemplate()
  const { mutateAsync, isPending } = useMutation({
    ...createMinuteTranscriptionTranscriptionIdMinutesPostMutation(),
  })

  const generateSummary = useCallback(
    async (sourceMinuteId: string | null): Promise<MinuteListItem> => {
      const minute = await mutateAsync({
        path: { transcription_id: transcriptionId },
        body: sourceMinuteId
          ? { source_minute_id: sourceMinuteId }
          : {
              template_name: defaultTemplate?.name ?? 'General',
              template_id: defaultTemplate?.id ?? null,
            },
      })
      await queryClient.invalidateQueries({
        queryKey:
          listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetQueryKey(
            { path: { transcription_id: transcriptionId } }
          ),
      })
      posthog.capture('generate_ai_minutes_started', {
        style: minute.template_name,
        source: 'speaker_editor',
      })
      return minute
    },
    [defaultTemplate, mutateAsync, queryClient, transcriptionId]
  )

  return { generateSummary, isGenerating: isPending }
}
