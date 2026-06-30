'use client'

import { Mic } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

import RecordingControl from './recording-control'

import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { DiscardConfirmDialog } from '@/components/audio/discard-dialog'
import { StartTranscriptionSection } from '@/components/audio/start-transcription-section'
import { TranscriptionForm } from '@/components/audio/types'
import { useTabCloseWarning } from '@/hooks/use-tab-close-warning'
import { useWakeLock } from '@/hooks/use-wake-lock'
import { useStartTranscription } from '@/hooks/useStartTranscription'
import { useRecordingDb } from '@/providers/transcription-db-provider'
import { Controller, FormProvider, useFormContext } from 'react-hook-form'
import { AudioDevice, MicrophonePermission } from './microphone-permission'
import { getFileExtensionFromBlob } from '@/lib/getFileExtension'

export function MicRecorderForm({
  initialDeviceId,
  initialDevices,
  onDiscard,
}: {
  initialDeviceId?: string
  initialDevices?: AudioDevice[]
  onDiscard?: () => void
} = {}) {
  const { isPending, onSubmit, form } = useStartTranscription()
  const watchBlob = form.watch('file')
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
            />
          )}
        />
        <StartTranscriptionSection
          isShowing={!!watchBlob}
          isPending={isPending}
        />
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
}: {
  recordedAudio: Blob | null
  setRecordedAudio: (blob: Blob | null) => void
  initialDeviceId?: string
  initialDevices?: AudioDevice[]
  onDiscard?: () => void
}) {
  // When a device is handed in pre-resolved (from the home page), permission is
  // already granted upstream — so skip the cold flow and start recording immediately.
  const autoStart = !!(initialDeviceId && initialDevices?.length)
  const { releaseWakeLock, requestWakeLock } = useWakeLock()
  const [error, setError] = useState<string | null>(null)
  const [audioDevices, setAudioDevices] = useState<AudioDevice[]>(
    initialDevices ?? []
  )
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>(
    initialDeviceId ?? ''
  )
  const [permissionGranted, setPermissionGranted] = useState<boolean>(
    !!(initialDeviceId && initialDevices?.length)
  )
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [showStopDialog, setShowStopDialog] = useState(false)
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

  const handlePermissionGranted = (devices: AudioDevice[]) => {
    setAudioDevices(devices)
    setSelectedDeviceId(devices[0].deviceId)
    setPermissionGranted(true)
    setError(null)
  }

  useTabCloseWarning(!!recordedAudio || isRecording)

  if (!permissionGranted || !audioDevices.length) {
    return (
      <div className="space-y-4">
        <MicrophonePermission
          onPermissionGranted={handlePermissionGranted}
          onError={setError}
        />
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>
    )
  }
  return (
    <div>
      {recordedAudio && (
        <>
          <div className="govuk-grid-row">
            <div className="govuk-grid-column-one-third">
              <h2 className="govuk-heading-m">Your recording:</h2>
            </div>
            <div className="govuk-grid-column-two-thirds">
              <audio
                src={URL.createObjectURL(recordedAudio)}
                controls
                className="w-full"
              />
              <div className="govuk-button-group govuk-!-margin-top-2">
                <a
                  role="button"
                  href={URL.createObjectURL(recordedAudio)}
                  download={`audio-file.${getFileExtensionFromBlob(recordedAudio)}`}
                  className="govuk-button govuk-button--secondary"
                >
                  Download audio
                </a>
                <button
                  type="button"
                  className="govuk-link link--warning"
                  onClick={() => setIsDialogOpen(true)}
                >
                  Discard recording
                </button>
              </div>
            </div>
          </div>
        </>
      )}
      {!recordedAudio && (
        <>
          <h2 className="govuk-heading-m flex items-center gap-2">
            <span className="relative mr-2 inline-flex size-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
              <span className="relative inline-flex size-3 rounded-full bg-red-600" />
            </span>
            Recording
          </h2>
          <div className="govuk-inset-text">
            This will record the audio from your device&apos;s microphone. That
            means only in-person meetings or calls that are played out loud will
            be picked up. Make sure you check there are sound waves appearing in
            the audio recorder. If not, refresh the page and make sure
            you&apos;ve allowed microphone access in your browser.
          </div>
        </>
      )}
      {isRecording && (
        <div>
          <RecordingControl
            stream={mediaRecorderRef.current?.stream || null}
            isRecording={isRecording}
            onStopRecording={stopRecording}
            onPauseStateChange={handlePauseStateChange}
            onDiscard={() => setIsDialogOpen(true)}
          />
        </div>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <AlertDialog open={showStopDialog} onOpenChange={setShowStopDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Stop Recording?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to stop recording? You won&apos;t be able to
              resume recording after stopping.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={stopRecording}>
              Stop Recording
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

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
