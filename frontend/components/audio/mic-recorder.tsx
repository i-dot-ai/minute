'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

import RecordingControl from './recording-control'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { DiscardConfirmDialog } from '@/components/audio/discard-dialog'
import { TranscriptionForm } from '@/components/audio/types'
import { useTabCloseWarning } from '@/hooks/use-tab-close-warning'
import { useWakeLock } from '@/hooks/use-wake-lock'
import { useStartTranscription } from '@/hooks/useStartTranscription'
import { useRecordingDb } from '@/providers/transcription-db-provider'
import { Controller, FormProvider, useFormContext } from 'react-hook-form'
import { AudioDevice } from './microphone-permission'

export function MicRecorderForm({
  initialDeviceId,
  initialDevices,
  onDiscard,
  onStarted,
}: {
  initialDeviceId?: string
  initialDevices?: AudioDevice[]
  onDiscard?: () => void
  onStarted?: (transcriptionId: string) => void
} = {}) {
  const { isError, onSubmit, form } = useStartTranscription(
    undefined,
    onStarted
  )
  const watchBlob = form.watch('file')
  // Set when the user chooses "Generate summary" in the stop dialog. Stopping the
  // recorder is async, so we wait for the audio blob to land before submitting.
  const [generateRequested, setGenerateRequested] = useState(false)

  useEffect(() => {
    if (generateRequested && watchBlob) {
      setGenerateRequested(false)
      form.handleSubmit(onSubmit)()
    }
  }, [generateRequested, watchBlob, form, onSubmit])

  return (
    <FormProvider {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <Controller
          name="file"
          control={form.control}
          render={({ field: { value, onChange } }) => (
            <MicRecorderComponent
              recordedAudio={value}
              setRecordedAudio={onChange}
              initialDeviceId={initialDeviceId}
              initialDevices={initialDevices}
              onDiscard={onDiscard}
              onGenerate={() => setGenerateRequested(true)}
            />
          )}
        />
        {isError && (
          <div className="govuk-!-margin-top-4">
            <p className="govuk-body">
              Something went wrong starting your summary. Please try again.
            </p>
            <button type="button" onClick={onDiscard} className="govuk-button">
              Start again
            </button>
          </div>
        )}
      </form>
    </FormProvider>
  )
}

function MicRecorderComponent({
  recordedAudio,
  setRecordedAudio,
  initialDeviceId,
  initialDevices,
  onDiscard,
  onGenerate,
}: {
  recordedAudio: Blob | null
  setRecordedAudio: (blob: Blob | null) => void
  initialDeviceId?: string
  initialDevices?: AudioDevice[]
  onDiscard?: () => void
  onGenerate?: () => void
}) {
  // When a device is handed in pre-resolved (from the home page), permission is
  // already granted upstream — so skip the cold flow and start recording immediately.
  const autoStart = !!(initialDeviceId && initialDevices?.length)
  const { releaseWakeLock, requestWakeLock } = useWakeLock()
  const [error, setError] = useState<string | null>(null)
  const selectedDeviceId = initialDeviceId ?? ''
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const form = useFormContext<TranscriptionForm>()
  const { removeRecording, addRecording, updateRecording } = useRecordingDb()
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)
  const mediaChunksRef = useRef<Blob[]>([])
  // Set when discarding mid-recording so onstop drops the audio instead of saving it.
  const discardingRef = useRef(false)
  const [isRecording, setIsRecording] = useState(false)

  const stopAllTracks = useCallback(() => {
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((track) => track.stop())
    }
    micStreamRef.current = null
    mediaRecorderRef.current = null

    setIsRecording(false)
    releaseWakeLock()
  }, [releaseWakeLock])

  const startRecording = useCallback(async () => {
    try {
      setError(null)
      mediaChunksRef.current = []
      const micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: selectedDeviceId,
          noiseSuppression: false,
          echoCancellation: false,
        },
      })
      micStreamRef.current = micStream
      const options = { mimeType: 'audio/webm' }
      const mediaRecorder = new MediaRecorder(micStream, options)
      mediaRecorderRef.current = mediaRecorder

      mediaRecorder.onstart = async () => {
        const recordingId = await addRecording(new Blob())
        form.setValue('recordingId', recordingId)
      }

      mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0) {
          mediaChunksRef.current.push(event.data)
          const recordingId = form.getValues('recordingId')
          if (recordingId && mediaChunksRef.current.length % 60 == 0) {
            const audioBlob = new Blob(mediaChunksRef.current, {
              type: 'audio/webm',
            })
            await updateRecording(recordingId, audioBlob)
          }
        }
      }

      mediaRecorder.onerror = () => {
        setError('Recording error occurred. Please try again.')
        // Don't call stopRecording here as it might cause a loop
        // Just clean up manually if needed
        stopAllTracks()
      }

      mediaRecorder.onstop = async () => {
        if (discardingRef.current) {
          discardingRef.current = false
          setRecordedAudio(null)
          const recordingId = form.getValues('recordingId')
          if (recordingId) {
            await removeRecording(recordingId)
          }
          stopAllTracks()
          onDiscard?.()
          return
        }
        if (mediaChunksRef.current.length > 0) {
          const audioBlob = new Blob(mediaChunksRef.current, {
            type: 'audio/webm',
          })
          setRecordedAudio(audioBlob)
          const recordingId = form.getValues('recordingId')
          if (recordingId) {
            await updateRecording(recordingId, audioBlob)
          }
        } else {
          setError(
            'No audio data was recorded. Please try again and ensure audio is shared.'
          )
        }
        stopAllTracks()
      }

      // Start recording
      setRecordedAudio(null)
      await requestWakeLock()
      mediaRecorder.start(1000) // Collect data every second
      setIsRecording(true)
    } catch (micError) {
      console.warn('Error occurred starting audio recording.', micError)
    }
    // Create a media recorder from the composed stream
  }, [
    addRecording,
    form,
    onDiscard,
    removeRecording,
    requestWakeLock,
    selectedDeviceId,
    setRecordedAudio,
    stopAllTracks,
    updateRecording,
  ])

  const stopRecording = useCallback(() => {
    // Prevent multiple calls to stopRecording
    if (!mediaRecorderRef.current || !isRecording) {
      return
    }
    try {
      // Only call stop() if the state is not 'inactive'
      if (mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      } else {
        stopAllTracks()
      }
    } catch {
      // Clean up streams even if stop fails
      stopAllTracks()
    }
  }, [isRecording, stopAllTracks])

  useEffect(() => {
    return () => {
      stopRecording()
    }
  }, [stopRecording])

  const hasAutoStarted = useRef(false)
  useEffect(() => {
    if (autoStart && !hasAutoStarted.current) {
      hasAutoStarted.current = true
      startRecording()
    }
  }, [autoStart, startRecording])

  const handlePauseStateChange = useCallback((paused: boolean) => {
    if (!mediaRecorderRef.current) {
      return
    }
    if (paused) {
      mediaRecorderRef.current.pause()
    } else {
      mediaRecorderRef.current.resume()
    }
  }, [])

  useTabCloseWarning(!!recordedAudio || isRecording)

  return (
    <div>
      {isRecording && (
        <>
          <div>
            <RecordingControl
              stream={mediaRecorderRef.current?.stream || null}
              isRecording={isRecording}
              onStopRecording={stopRecording}
              onPauseStateChange={handlePauseStateChange}
              onDiscard={() => setIsDialogOpen(true)}
              onGenerate={onGenerate}
            />
          </div>
        </>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <DiscardConfirmDialog
        open={isDialogOpen}
        setOpen={setIsDialogOpen}
        onClickConfirm={() => {
          setIsDialogOpen(false)
          // Mid-recording: stop first; onstop handles cleanup once the recorder flushes.
          if (isRecording && mediaRecorderRef.current) {
            discardingRef.current = true
            stopRecording()
            return
          }
          setRecordedAudio(null)
          const recordingId = form.getValues('recordingId')
          if (recordingId) {
            removeRecording(recordingId)
          }
          onDiscard?.()
        }}
      />
    </div>
  )
}
