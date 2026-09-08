import { TranscriptionForm } from '@/components/audio/types'
import {
  createRecordingRecordingsPostMutation,
  createTranscriptionTranscriptionsPostMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { getFileExtension } from '@/lib/getFileExtension'
import {
  measureAudioDurationSec,
  storeRecordingDurationSec,
} from '@/lib/recording-duration'
import { useRecordingDb } from '@/providers/transcription-db-provider'
import { useMutation } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import posthog from 'posthog-js'
import { useCallback, useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useDefaultTemplate } from '@/hooks/useDefaultTemplate'

export const useStartTranscription = (
  defaultValues?: Partial<TranscriptionForm>,
  onStarted?: (transcriptionId: string) => void
) => {
  const router = useRouter()
  const { removeRecording } = useRecordingDb()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isError, setIsError] = useState(false)
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
      setIsError(false)
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
        // Measured for the status page's estimate, but best-effort: it must not
        // gate transcription. Start it alongside the upload and await only the
        // upload, so a slow/never-settling measurement can't block creating the
        // transcription. (measureAudioDurationSec is itself timeout-bounded.)
        const durationPromise = measureAudioDurationSec(file)
        await uploadBlob({ file, uploadUrl: recordingData.upload_url })
        const transcriptionData = await createTranscription({
          body: {
            recording_id: recordingData.id,
            template_id: template.id,
            template_name: template.name,
            agenda,
          },
        })
        // Store before navigating so the status page can read the estimate on
        // mount. Safe to await now that transcription is already created and the
        // measurement is bounded.
        storeRecordingDurationSec(transcriptionData.id, await durationPromise)
        if (recordingId) {
          await removeRecording(recordingId)
        }
        if (onStarted) {
          onStarted(transcriptionData.id)
        } else {
          router.push(`/transcriptions/${transcriptionData.id}`)
        }
      } catch {
        setIsSubmitting(false)
        setIsError(true)
      }
    },
    [
      createRecording,
      createTranscription,
      defaultValues?.recordingId,
      onStarted,
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

  const defaultTemplate = useDefaultTemplate()
  useEffect(() => {
    if (defaultTemplate && !form.formState.dirtyFields.template) {
      form.setValue('template', defaultTemplate)
    }
  }, [defaultTemplate, form])

  return {
    isPending: isSubmitting,
    isError,
    onSubmit,
    form,
  }
}
