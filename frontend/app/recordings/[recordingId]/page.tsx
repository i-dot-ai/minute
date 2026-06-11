'use client'

import { DiscardConfirmDialog } from '@/components/audio/discard-dialog'
import { StartTranscriptionSection } from '@/components/audio/start-transcription-section'
import { useStartTranscription } from '@/hooks/useStartTranscription'
import { getFileExtensionFromBlob } from '@/lib/getFileExtension'
import {
  RecordingDbItem,
  useRecordingDb,
} from '@/providers/transcription-db-provider'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, TriangleAlert } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import posthog from 'posthog-js'
import { useState } from 'react'
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
  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
        <ol className="govuk-breadcrumbs__list">
          <li className="govuk-breadcrumbs__list-item">
            <Link className="govuk-breadcrumbs__link" href="/">Home</Link>
          </li>
          <li className="govuk-breadcrumbs__list-item">
            <Link className="govuk-breadcrumbs__link" href="/transcriptions">Transcriptions</Link>
          </li>
        </ol>
      </nav>
      <h1 className="govuk-heading-xl">Upload an offline recording</h1>
      {isLoading && (
        <>
          <Loader2 className="animate-spin" />
          <p className="govuk-body">Loading...</p>
        </>
      )}
      {error && (
        <>
          <TriangleAlert />
          <p className="govuk-body">Recording with id {recordingId} not found!</p>
        </>
      )}
      {recording && <RecordingUploadForm recording={recording} />}
    </div>
  )
}

function RecordingUploadForm({ recording }: { recording: RecordingDbItem }) {
  const { form, isPending, onSubmit } = useStartTranscription({
    file: recording.blob,
    recordingId: recording.recording_id,
  })
  const { removeRecording } = useRecordingDb()
  const router = useRouter()
  const queryClient = useQueryClient()
  const [discardDialogOpen, setDiscardDialogOpen] = useState(false)

  const handleDiscardConfirm = async () => {
    await removeRecording(recording.recording_id)
    queryClient.invalidateQueries({ queryKey: ['list-db-recordings'] })
    posthog.capture('offline_recording_deleted', {
      size: recording.blob.size,
    })
    setDiscardDialogOpen(false)
    router.push('/transcriptions')
  }

  return (
    <FormProvider {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <div className="govuk-!-margin-bottom-9">
          <h2 className="govuk-heading-l">Your recording</h2>
          <audio src={URL.createObjectURL(recording.blob)} controls className="w-full" />
          <div className="govuk-button-group govuk-!-margin-top-2">
            <a role="button" href={URL.createObjectURL(recording.blob)} download={`audio-file.${getFileExtensionFromBlob(recording.blob)}`} className="govuk-button govuk-button--secondary">Save Recording</a>
            <button type="button" className="govuk-link link--warning" onClick={() => setDiscardDialogOpen(true)}>Discard recording</button>
          </div>
        </div>
        <StartTranscriptionSection isPending={isPending} isShowing={true} />
      </form>
      <DiscardConfirmDialog
        open={discardDialogOpen}
        setOpen={setDiscardDialogOpen}
        onClickConfirm={handleDiscardConfirm}
      />
    </FormProvider>
  )
}
