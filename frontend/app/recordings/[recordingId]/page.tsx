'use client'

import AudioPlayerComponent from '@/components/audio/audio-player'
import { StartTranscriptionSection } from '@/components/audio/start-transcription-section'
import { useStartTranscription } from '@/hooks/useStartTranscription'
import {
  RecordingDbItem,
  useRecordingDb,
} from '@/providers/transcription-db-provider'
import { useQuery } from '@tanstack/react-query'
import { Loader2, TriangleAlert } from 'lucide-react'
import { FormProvider } from 'react-hook-form'

export default function RecordingPage({
  params: { recordingId },
}: {
  params: { recordingId: string }
}) {
  const { getRecording } = useRecordingDb()
  const {
    data: recording,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['db-recording-get', recordingId],
    queryFn: async () => await getRecording(recordingId),
  })
  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl">
        <h1 className="mb-6 text-3xl font-bold">Upload an offline recording</h1>
        <p className="flex gap-2">
          <Loader2 className="animate-spin" /> Loading...
        </p>
      </div>
    )
  }
  if (error || !recording) {
    return (
      <div className="mx-auto max-w-3xl">
        <h1 className="mb-6 text-3xl font-bold">Upload an offline recording</h1>
        <p className="flex gap-1">
          <TriangleAlert /> Recording with id {recordingId} not found!
        </p>
      </div>
    )
  }
  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-6 text-3xl font-bold">Upload an offline recording</h1>
      <RecordingUploadForm recording={recording} />
    </div>
  )
}

function RecordingUploadForm({ recording }: { recording: RecordingDbItem }) {
  const {
    form,
    isPending,
    onSubmit,
    templates,
    selectedTemplate,
    isLoadingTemplates,
  } = useStartTranscription({
    file: recording.blob,
    recordingId: recording.recording_id,
  })

  return (
    <FormProvider {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <AudioPlayerComponent audioBlob={recording.blob} />
        <StartTranscriptionSection
          isPending={isPending}
          isShowing={true}
          templates={templates}
          selectedTemplate={selectedTemplate}
          isLoadingTemplates={isLoadingTemplates}
        />
      </form>
    </FormProvider>
  )
}
