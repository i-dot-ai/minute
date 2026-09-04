'use client'

import React, { useEffect, useRef, useState } from 'react'
import { Pause, Play } from 'lucide-react'
import RecordingTimer from './recording-timer'
import { GenerateSummaryDialog } from './generate-summary-dialog'
import MinuteVisualizer from './minute-visualizer'

interface RecordingControlProps {
  stream: MediaStream | null
  isRecording: boolean
  onStopRecording: () => void
  recorderControls?: {
    togglePauseResume?: () => void
    isPaused?: boolean
  }
  onPauseStateChange?: (isPaused: boolean) => void
  onDiscard?: () => void
  onGenerate?: () => void
}

export default function RecordingControl({
  stream,
  isRecording,
  onStopRecording,
  recorderControls,
  onPauseStateChange,
  onDiscard,
  onGenerate,
}: RecordingControlProps) {
  const animationRef = useRef<number | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const dataArrayRef = useRef<Uint8Array | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const [showStopDialog, setShowStopDialog] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [mediaTracks, setMediaTracks] = useState<MediaStreamTrack[]>([])
  const [announcement, setAnnouncement] = useState('')
  // Silence detection: flagged after a sustained quiet spell so natural speech
  // pauses don't trigger it. Mirrored in a ref for the rAF draw loop.
  const [audioSilent, setAudioSilent] = useState(false)
  const audioSilentRef = useRef(false)
  const silenceStartRef = useRef<number | null>(null)
  const recordingHeadingRef = useRef<HTMLHeadingElement>(null)

  // The start button unmounts when the recorder UI replaces it, which would
  // drop keyboard/screen-reader focus to <body>. Land it on the heading instead.
  useEffect(() => {
    if (isRecording) {
      setAnnouncement('Recording started')
      const id = setTimeout(() => recordingHeadingRef.current?.focus(), 0)
      return () => clearTimeout(id)
    }
  }, [isRecording])

  // Initialize media tracks from the stream if available
  useEffect(() => {
    if (stream) {
      const tracks = stream.getAudioTracks()
      setMediaTracks(tracks)
    }
  }, [stream])

  // Handle the recorder controls isPaused state if available
  useEffect(() => {
    if (recorderControls?.isPaused !== undefined) {
      setIsPaused(recorderControls.isPaused)
    }
  }, [recorderControls?.isPaused])

  useEffect(() => {
    // Restart silence tracking whenever the stream or pause state changes.
    silenceStartRef.current = null

    // Check if we have a valid stream with audio tracks
    const isValidStream =
      stream && stream.active && stream.getAudioTracks().length > 0

    if (!isValidStream || !isRecording) {
      // Clean up if not recording or invalid stream
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(console.error)
        audioContextRef.current = null
      }
      analyserRef.current = null
      dataArrayRef.current = null
      return
    }

    // Initialize audio context and analyzer
    try {
      // Always recreate the audio context when the stream changes
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(console.error)
        audioContextRef.current = null
        analyserRef.current = null
      }

      audioContextRef.current = new AudioContext()
      analyserRef.current = audioContextRef.current.createAnalyser()
      analyserRef.current.fftSize = 256
      analyserRef.current.smoothingTimeConstant = 0.7

      const bufferLength = analyserRef.current.frequencyBinCount
      dataArrayRef.current = new Uint8Array(bufferLength)

      // Create a media stream source and connect it to the analyzer
      const source = audioContextRef.current.createMediaStreamSource(stream)
      source.connect(analyserRef.current)
    } catch (error) {
      console.error('Error setting up audio context', error)
    }

    // Sample the analyser on each frame purely to detect sustained silence.
    // The visual rendering is handled separately by <MinuteVisualizer />.
    const detectSilence = () => {
      const analyser = analyserRef.current
      const dataArray = dataArrayRef.current

      if (isRecording && analyser && dataArray) {
        analyser.getByteFrequencyData(dataArray)

        const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
        const hasAudioData = average > 5

        if (hasAudioData) {
          silenceStartRef.current = null
          if (audioSilentRef.current) {
            audioSilentRef.current = false
            setAudioSilent(false)
          }
        } else if (!isPaused) {
          silenceStartRef.current ??= Date.now()
          if (
            Date.now() - silenceStartRef.current > 3000 &&
            !audioSilentRef.current
          ) {
            audioSilentRef.current = true
            setAudioSilent(true)
          }
        }
      }

      animationRef.current = requestAnimationFrame(detectSilence)
    }

    detectSilence()

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [stream, isRecording, isPaused])

  const togglePause = () => {
    setAnnouncement(isPaused ? 'Recording resumed' : 'Recording paused')
    if (recorderControls?.togglePauseResume) {
      recorderControls.togglePauseResume()
    } else if (stream && mediaTracks.length > 0) {
      const newPausedState = !isPaused
      mediaTracks.forEach((track) => {
        const newTrack = track
        newTrack.enabled = !newPausedState
      })
      setIsPaused(newPausedState)
      if (onPauseStateChange) {
        onPauseStateChange(newPausedState)
      }
    }
  }

  const handleStopRecording = () => {
    setShowStopDialog(true)
  }

  const confirmStop = () => {
    onGenerate?.()
    onStopRecording()
    setShowStopDialog(false)
  }

  return (
    <div className="space-y-4">
      <p className="govuk-visually-hidden" role="status">
        {announcement}
      </p>
      <p className="govuk-visually-hidden" role="status">
        {isRecording && !isPaused && audioSilent
          ? 'No audio detected from your microphone'
          : ''}
      </p>
      <div className="govuk-!-padding-5 bg-(--govuk-surface-background-colour)">
        {isRecording && (
          <div className="flex justify-between">
            <h2
              ref={recordingHeadingRef}
              tabIndex={-1}
              className="govuk-heading-m flex items-center gap-2"
            >
              <span
                aria-hidden="true"
                className="relative mr-2 inline-flex size-3"
              >
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75 motion-reduce:animate-none" />
                <span className="relative inline-flex size-3 rounded-full bg-red-600" />
              </span>
              Recording
            </h2>
            <RecordingTimer isRecording={isRecording} isPaused={isPaused} />
          </div>
        )}
        <div className="govuk-!-margin-bottom-4 mx-auto border-[#8eb8dc]">
          <div className="mx-auto">
            <MinuteVisualizer
              stream={stream}
              isRecording={isRecording}
              isPaused={isPaused}
            />
            {!isRecording && (
              <p className="govuk-body">
                Audio visualization will appear here when recording
              </p>
            )}
            {isRecording && !stream && (
              <p className="govuk-body">Connecting to audio stream...</p>
            )}
          </div>
        </div>
        {isRecording && (
          <div className="govuk-button-group govuk-!-margin-bottom-0 flex w-full gap-2">
            <button
              type="button"
              onClick={togglePause}
              className="govuk-button govuk-button--secondary min-w-32"
            >
              {isPaused ? (
                <>
                  <Play className="size-4" />
                  Resume
                </>
              ) : (
                <>
                  <Pause className="size-4" />
                  Pause
                </>
              )}
            </button>
            <button
              type="button"
              onClick={handleStopRecording}
              className="govuk-button"
            >
              Stop recording and save
            </button>
            {onDiscard && (
              <button
                type="button"
                className="govuk-link link--warning ml-auto"
                onClick={onDiscard}
              >
                Discard recording
              </button>
            )}
          </div>
        )}
      </div>

      <GenerateSummaryDialog
        open={showStopDialog}
        warningText="You won't be able to resume recording after stopping."
        onOpenChange={setShowStopDialog}
        onConfirm={confirmStop}
      />
    </div>
  )
}
