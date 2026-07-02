'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

import { Alert, AlertDescription } from '@/components/ui/alert'

import { AudioDevice } from '@/components/audio/microphone-permission'
import RecordingControl from '@/components/audio/recording-control'
import { TranscriptionForm } from '@/components/audio/types'
import { useTabCloseWarning } from '@/hooks/use-tab-close-warning'
import { useWakeLock } from '@/hooks/use-wake-lock'
import { useStartTranscription } from '@/hooks/useStartTranscription'
import { useRecordingDb } from '@/providers/transcription-db-provider'
import { Controller, FormProvider, useFormContext } from 'react-hook-form'

export const TabRecorderForm = ({
  initialDeviceId,
  initialDevices,
  screenStream,
  onDiscard,
  onStarted,
}: {
  initialDeviceId?: string
  initialDevices?: AudioDevice[]
  screenStream?: MediaStream | null
  onDiscard?: () => void
  onStarted?: (transcriptionId: string) => void
} = {}) => {
  const { isError, onSubmit, form } = useStartTranscription(undefined, onStarted)
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
          control={form.control}
          name="file"
          render={({ field: { onChange, value } }) => (
            <TabRecorder
              recordedAudio={value}
              setRecordedAudio={(blob) => onChange(blob)}
              initialDeviceId={initialDeviceId}
              initialDevices={initialDevices}
              initialScreenStream={screenStream}
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
            <button
              type="button"
              onClick={onDiscard}
              className="govuk-button"
            >
              Start again
            </button>
          </div>
        )}
      </form>
    </FormProvider>
  )
}

function TabRecorder({
  setRecordedAudio,
  recordedAudio,
  initialDeviceId,
  initialDevices,
  initialScreenStream,
  onDiscard,
  onGenerate,
}: {
  recordedAudio: Blob | null
  setRecordedAudio: (blob: Blob | null) => void
  initialDeviceId?: string
  initialDevices?: AudioDevice[]
  initialScreenStream?: MediaStream | null
  onDiscard?: () => void
  onGenerate?: () => void
}) {
  // When a device is handed in pre-resolved (from the home page), permission is
  // already granted upstream — so skip the cold flow and start recording immediately.
  const autoStart = !!(initialDeviceId && initialDevices?.length)
  const { requestWakeLock, releaseWakeLock } = useWakeLock()
  const { updateRecording, addRecording } = useRecordingDb()
  const [err, setError] = useState<string | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const audioContext = useRef<AudioContext | null>(null)
  const recordingGain = useRef<GainNode | null>(null)
  const form = useFormContext<TranscriptionForm>()
  const selectedDeviceId = initialDeviceId ?? ''
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const mediaChunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const screenStreamRef = useRef<MediaStream | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)
  useTabCloseWarning(isRecording || !!recordedAudio)

  const stopAllTracks = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        track.stop()
      })
    }
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach((track) => track.stop())
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((track) => track.stop())
    }
    streamRef.current = null
    micStreamRef.current = null
    screenStreamRef.current = null
    mediaRecorderRef.current = null

    // Close the audio context here (on actual stop) rather than in a mount
    // cleanup — under Strict Mode the mount cleanup fires mid-start and would
    // close the freshly created context, silencing the recording.
    if (audioContext.current) {
      audioContext.current.close().catch(console.error)
      audioContext.current = null
    }

    setIsRecording(false)
    releaseWakeLock()
  }, [releaseWakeLock])

  // Define wakelock changed  before it's used in useEffect
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

  // stop recording on page unmount
  useEffect(() => {
    return () => {
      stopRecording()
    }
  }, [stopRecording])

  // Handle pause state changes
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

  const startRecording = useCallback(async () => {
    setError(null)
    mediaChunksRef.current = []

    try {
      // The home page opens the share picker on click and hands the stream in.
      const screenStream = initialScreenStream
      if (!screenStream) {
        throw new Error('No screen share available. Please start again.')
      }

      // Check if we have an audio track from the tab
      if (!screenStream.getAudioTracks().length) {
        // Clean up the stream if no audio tracks
        screenStream.getTracks().forEach((track) => track.stop())
        throw new Error(
          "No audio track available from the tab. When sharing, please switch on 'Share audio' in the dialog."
        )
      }
      screenStreamRef.current = screenStream

      // Create a new audio context for processing audio and for pausing
      const newAudioContext = new AudioContext()
      // Browsers create the context suspended unless started from a user gesture.
      // Since recording now auto-starts after the share picker, resume it so audio
      // actually flows into the recording destination.
      if (newAudioContext.state === 'suspended') {
        await newAudioContext.resume()
      }
      const destination = newAudioContext.createMediaStreamDestination()
      audioContext.current = newAudioContext

      // Create a gain node for pause/resume functionality
      const gainNode = newAudioContext.createGain()
      gainNode.gain.value = 1.0 // Start with full volume
      recordingGain.current = gainNode

      // Add screen audio to the composed stream
      const screenSource = newAudioContext.createMediaStreamSource(screenStream)
      const screenGain = newAudioContext.createGain()
      screenGain.gain.value = 1.0
      screenSource.connect(screenGain).connect(gainNode).connect(destination)

      // Merge both audio streams with gain control
      try {
        const micStream = await navigator.mediaDevices.getUserMedia({
          audio: { deviceId: selectedDeviceId },
        })
        micStreamRef.current = micStream
        // Add mic audio to the composed stream
        const micSource = newAudioContext.createMediaStreamSource(micStream)
        const micGain = newAudioContext.createGain()
        micGain.gain.value = 1.0
        micSource.connect(micGain).connect(gainNode).connect(destination)

        // Add the merged audio track
      } catch (micError) {
        console.warn(
          'Could not access microphone. Recording only tab audio.',
          micError
        )
      }

      const composedStream = new MediaStream()
      destination.stream.getAudioTracks().forEach((track) => {
        composedStream.addTrack(track)
      })
      streamRef.current = composedStream

      // Create a media recorder from the composed stream
      const options = { mimeType: 'audio/webm' }
      const mediaRecorder = new MediaRecorder(composedStream, options)
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
      await requestWakeLock()
      mediaRecorder.start(1000) // Collect data every second
      setIsRecording(true)
    } catch (error) {
      setError(
        error instanceof Error ? error.message : 'An unknown error occurred'
      )
      setIsRecording(false)
    }
  }, [
    addRecording,
    form,
    initialScreenStream,
    requestWakeLock,
    selectedDeviceId,
    setRecordedAudio,
    stopAllTracks,
    updateRecording,
  ])

  const hasAutoStarted = useRef(false)
  useEffect(() => {
    if (autoStart && !hasAutoStarted.current) {
      hasAutoStarted.current = true
      startRecording()
    }
  }, [autoStart, startRecording])

  return (
    <div className="space-y-4">
      {isRecording ? (
        <RecordingControl
          stream={streamRef.current}
          isRecording={isRecording}
          onStopRecording={stopRecording}
          onPauseStateChange={handlePauseStateChange}
          onGenerate={onGenerate}
        />
      ) : (
        err && (
          <div className="govuk-button-group">
            <button
              type="button"
              onClick={() => onDiscard?.()}
              className="govuk-link link--warning"
            >
              Back
            </button>
          </div>
        )
      )}

      {err && (
        <Alert variant="destructive">
          <AlertDescription>{err}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}

export default TabRecorder
