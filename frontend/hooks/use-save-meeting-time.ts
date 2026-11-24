import {
  MeetingTime,
  toApiMeetingDatetime,
  toMeetingTime,
} from '@/components/audio/meeting-time-field'
import {
  getTranscriptionTranscriptionsTranscriptionIdGetQueryKey,
  listTranscriptionsTranscriptionsGetQueryKey,
  saveTranscriptionTranscriptionsTranscriptionIdPatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import posthog from 'posthog-js'
import { useCallback } from 'react'

export const useSaveMeetingTime = (transcriptionId: string) => {
  const queryClient = useQueryClient()
  const { mutate } = useMutation({
    ...saveTranscriptionTranscriptionsTranscriptionIdPatchMutation(),
    onSuccess() {
      queryClient.invalidateQueries({
        queryKey: listTranscriptionsTranscriptionsGetQueryKey(),
      })
      queryClient.invalidateQueries({
        queryKey: getTranscriptionTranscriptionsTranscriptionIdGetQueryKey({
          path: { transcription_id: transcriptionId },
        }),
      })
      posthog.capture('changed_meeting_date', { transcriptionId })
    },
  })

  const save = useCallback(
    (meetingTime: MeetingTime | undefined, savedDatetime?: string | null) => {
      const saved =
        savedDatetime &&
        toApiMeetingDatetime(toMeetingTime(new Date(savedDatetime)))
      if (toApiMeetingDatetime(meetingTime) === saved) return
      mutate({
        path: { transcription_id: transcriptionId },
        body: { meeting_datetime: toApiMeetingDatetime(meetingTime) },
      })
    },
    [mutate, transcriptionId]
  )

  return { save }
}
