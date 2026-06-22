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
import { useCallback, useState } from 'react'
import { useForm } from 'react-hook-form'

export const useStartTranscription = (
  defaultValues?: Partial<TranscriptionForm>
) => {
  const router = useRouter()
  const { removeRecording } = useRecordingDb()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { mutateAsync: createTranscription } = useMutation({
    ...createTranscriptionTranscriptionsPostMutation(),
  })
  const { mutateAsync: createRecording } = useMutation({
    ...createRecordingRecordingsPostMutation(),
  })
  const { mutateAsync: uploadBlob } = useMutation({
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
      setIsSubmitting(true)
      try {
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

        const recordingData = await createRecording({
          body: { file_extension },
        })
        await uploadBlob({ file, uploadUrl: recordingData.upload_url })
        const transcriptionData = await createTranscription({
          body: {
            recording_id: recordingData.id,
            template_id: template.id,
            template_name: template.name,
            agenda,
          },
        })
        if (recordingId) {
          await removeRecording(recordingId)
        }
        router.push(`/transcriptions/${transcriptionData.id}`)
      } catch {
        setIsSubmitting(false)
      }
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
      template: {
        name: 'General',
        description:
          'Standard meeting summary with key points, decisions, and action items',
        agenda_usage: 'optional',
        id: null,
      },
      ...defaultValues,
    },
  })
  return {
    isPending: isSubmitting,
    onSubmit,
    form,
  }
}
