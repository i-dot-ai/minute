'use client'

import { Mic } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

import { DiscardConfirmDialog } from '@/components/audio/discard-dialog'
import {
  AudioDevice,
  MicrophonePermission,
} from '@/components/audio/microphone-permission'
import RecordingControl from '@/components/audio/recording-control'
import { StartTranscriptionSection } from '@/components/audio/start-transcription-section'
import { InstructionsTabs } from '@/components/audio/tab-recorder/instructions'
import { TranscriptionForm } from '@/components/audio/types'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useTabCloseWarning } from '@/hooks/use-tab-close-warning'
import { useWakeLock } from '@/hooks/use-wake-lock'
import { useStartTranscription } from '@/hooks/useStartTranscription'
import { useRecordingDb } from '@/providers/transcription-db-provider'
import { Controller, FormProvider, useFormContext } from 'react-hook-form'
import AudioPlayerComponent from '../audio-player'

export const TabRecorderForm = () => {
  const {
    isPending,
    onSubmit,
    form,
    templates,
    isLoadingTemplates,
    selectedTemplate,
  } = useStartTranscription()
  const watchBlob = form.watch('file')

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
            />
          )}
        />
        <StartTranscriptionSection
          isShowing={!!watchBlob}
          isPending={isPending}
          templates={templates}
          isLoadingTemplates={isLoadingTemplates}
          selectedTemplate={selectedTemplate}
        />
      </form>
    </FormProvider>
  )
}

function TabRecorder({
  setRecordedAudio,
  recordedAudio,
}: {
  recordedAudio: Blob | null
  setRecordedAudio: (blob: Blob | null) => void
}) {
  const { requestWakeLock, releaseWakeLock } = useWakeLock()
  const { updateRecording, addRecording, removeRecording } = useRecordingDb()
  const [err, setError] = useState<string | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [discardDialogOpen, setDiscardDialogOpen] = useState(false)
  const audioContext = useRef<AudioContext | null>(null)
  const recordingGain = useRef<GainNode | null>(null)
  const form = useFormContext<TranscriptionForm>()
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('')
  const [permissionGranted, setPermissionGranted] = useState<boolean>(false)
  const [audioDevices, setAudioDevices] = useState<AudioDevice[]>([])
  const handlePermissionGranted = (devices: AudioDevice[]) => {
    setAudioDevices(devices)
    setSelectedDeviceId(devices[0].deviceId)
    setPermissionGranted(true)
    setError(null)
  }
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
    mediaRecorderRef.current = null

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
  // Clean up audio context on page unmount
  useEffect(() => {
    return () => {
      if (audioContext.current) {
        audioContext.current.close().catch(console.error)
      }
    }
  }, [])

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
      if (!navigator.mediaDevices?.getDisplayMedia) {
        throw new Error(
          'Screen capture is not supported in this browser. Please use Chrome or Edge.'
        )
      }

      // First get the display media stream (tab capture)
      const screenStream = await navigator.mediaDevices.getDisplayMedia({
        video: true, // Request video without specific constraints
        audio: true, // Request audio
      })

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
    requestWakeLock,
    selectedDeviceId,
    setRecordedAudio,
    stopAllTracks,
    updateRecording,
  ])

  if (!permissionGranted || !audioDevices.length) {
    return (
      <MicrophonePermission
        onPermissionGranted={handlePermissionGranted}
        onError={setError}
      />
    )
  }

  return (
    <div className="space-y-4">
      {recordedAudio ? (
        <div className="mt-4 space-y-3">
          <AudioPlayerComponent audioBlob={recordedAudio} />
          <div className="flex justify-end">
            <Button
              type="button"
              onClick={() => setDiscardDialogOpen(true)}
              variant="outline"
              size="sm"
            >
              Discard Recording
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col space-y-4">
          {!isRecording ? (
            <>
              <div className="space-y-4 py-2">
                <InstructionsTabs />
              </div>
              <span className="mb-2 text-sm font-medium">
                Choose your microphone:
              </span>
              <Select
                onValueChange={setSelectedDeviceId}
                disabled={isRecording}
                value={selectedDeviceId}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select microphone" />
                </SelectTrigger>
                <SelectContent>
                  {audioDevices.map((device) => (
                    <SelectItem key={device.deviceId} value={device.deviceId}>
                      {device.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button type="button" onClick={startRecording}>
                <Mic className="mr-2 size-4" />
                Start Recording Virtual Meeting
              </Button>
            </>
          ) : (
            <div className="space-y-4">
              <RecordingControl
                stream={streamRef.current}
                isRecording={isRecording}
                onStopRecording={stopRecording}
                onPauseStateChange={handlePauseStateChange}
              />
            </div>
          )}
        </div>
      )}

      {err && (
        <Alert variant="destructive">
          <AlertDescription>{err}</AlertDescription>
        </Alert>
      )}
      <DiscardConfirmDialog
        open={discardDialogOpen}
        setOpen={setDiscardDialogOpen}
        onClickConfirm={() => {
          setRecordedAudio(null)
          setDiscardDialogOpen(false)
          const recordingId = form.getValues('recordingId')
          if (recordingId) {
            removeRecording(recordingId)
          }
        }}
      />
    </div>
  )
}

export default TabRecorder
