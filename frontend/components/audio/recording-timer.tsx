'use client'

import { useEffect, useRef, useState } from 'react'

interface RecordingTimerProps {
  isRecording: boolean
  isPaused: boolean
}

// Format milliseconds as mm:ss, expanding to h:mm:ss once past an hour.
const formatElapsed = (ms: number): string => {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000))
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  const pad = (n: number) => n.toString().padStart(2, '0')
  return hours > 0
    ? `${hours}:${pad(minutes)}:${pad(seconds)}`
    : `${pad(minutes)}:${pad(seconds)}`
}

/**
 * Wall-clock recording timer.
 *
 * Elapsed time is derived from timestamps rather than an incrementing counter
 * so it stays accurate when the tab is backgrounded (where setInterval is
 * throttled). Paused time is subtracted, matching MediaRecorder.pause() which
 * excludes paused spans from the recorded audio's duration.
 */
export default function RecordingTimer({
  isRecording,
  isPaused,
}: RecordingTimerProps) {
  const startRef = useRef<number | null>(null)
  const pausedAccumRef = useRef(0)
  const pauseStartedRef = useRef<number | null>(null)
  const [elapsedMs, setElapsedMs] = useState(0)

  // Start / reset on recording start and stop.
  useEffect(() => {
    if (isRecording) {
      startRef.current = Date.now()
      pausedAccumRef.current = 0
      pauseStartedRef.current = null
      setElapsedMs(0)
    } else {
      startRef.current = null
      setElapsedMs(0)
    }
  }, [isRecording])

  // Track total time spent paused so it can be subtracted from elapsed.
  useEffect(() => {
    if (!isRecording) return
    if (isPaused) {
      pauseStartedRef.current = Date.now()
    } else if (pauseStartedRef.current != null) {
      pausedAccumRef.current += Date.now() - pauseStartedRef.current
      pauseStartedRef.current = null
    }
  }, [isPaused, isRecording])

  // Refresh the display once a second while actively recording.
  useEffect(() => {
    if (!isRecording || isPaused) return
    const tick = () => {
      if (startRef.current == null) return
      setElapsedMs(Date.now() - startRef.current - pausedAccumRef.current)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [isRecording, isPaused])

  if (!isRecording) return null

  return (
    <span
      role="timer"
      aria-label={`Elapsed recording time ${formatElapsed(elapsedMs)}`}
      className="govuk-body govuk-!-font-weight-bold tabular-nums"
    >
      {formatElapsed(elapsedMs)}
    </span>
  )
}
