import { TranscriptionForm } from '@/components/audio/types'
import {
  createRecordingRecordingsPostMutation,
  createTranscriptionTranscriptionsPostMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { getFileExtension } from '@/lib/getFileExtension'
import { useRecordingDb } from '@/providers/transcription-db-provider'
import { useMutation } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import posthog from 'posthog-js'
import { useCallback } from 'react'
import { useForm } from 'react-hook-form'

export const useStartTranscription = (
  defaultValues?: Partial<TranscriptionForm>
) => {
  const router = useRouter()
  const { removeRecording } = useRecordingDb()
  const { mutateAsync: createTranscription, isPending: isCreating } =
    useMutation({
      ...createTranscriptionTranscriptionsPostMutation(),
    })
  const { mutateAsync: createRecording, isPending: isConfirming } = useMutation(
    {
      ...createRecordingRecordingsPostMutation(),
    }
  )
  const { mutateAsync: uploadBlob, isPending: isUploading } = useMutation({
    mutationFn: async ({
      uploadUrl,
      file,
    }: {
      uploadUrl: string
      file: Blob | File
    }) => {
      const uploadResponse = await fetch(uploadUrl, {
        method: 'PUT',
        body: file,
        headers: {
          'x-ms-blob-type': 'BlockBlob',
        },
      })
      if (!uploadResponse.ok) {
        throw new Error('Failed to upload file to S3')
      }
    },
  })

  const onSubmit = useCallback(
    async ({ file, template, agenda, recordingId }: TranscriptionForm) => {
      if (!file) {
        return
      }
      const isFile = file instanceof File
      const source = !!defaultValues?.recordingId
        ? 'offline-recording'
        : isFile
          ? 'upload'
          : 'recording'
      const file_extension = isFile ? getFileExtension(file.name) : 'webm'
      posthog.capture('transcription_started', {
        file_type: file.type || '',
        source,
      })
      const now = new Date()
      const day = now.toLocaleDateString('en-GB', { weekday: 'long' })
      const hours = now.getHours()
      const period =
        hours < 5 || hours >= 21
          ? 'night'
          : hours < 12
            ? 'morning'
            : hours < 19
              ? 'afternoon'
              : 'evening'
      const title = `${day} ${period} ${source}`
      await createRecording(
        { body: { file_extension } },
        {
          onSuccess: async (recordingData) => {
            await uploadBlob(
              { file, uploadUrl: recordingData.upload_url },
              {
                onSuccess: async () => {
                  createTranscription(
                    {
                      body: {
                        recording_id: recordingData.id,
                        title,
                        template_id: template.id,
                        template_name: template.name,
                        agenda,
                      },
                    },
                    {
                      onSuccess: async (transcriptionData) => {
                        if (recordingId) {
                          await removeRecording(recordingId)
                        }
                        router.push(`/transcriptions/${transcriptionData.id}`)
                      },
                    }
                  )
                },
              }
            )
          },
        }
      )
    },
    [
      createRecording,
      createTranscription,
      defaultValues?.recordingId,
      removeRecording,
      router,
      uploadBlob,
    ]
  )
  const form = useForm<TranscriptionForm>({
    defaultValues: {
      file: null,
      template: { name: 'General', agenda_usage: 'optional' },
      ...defaultValues,
    },
  })
  return {
    isPending: isCreating || isConfirming || isUploading,
    onSubmit,
    form,
  }
}
