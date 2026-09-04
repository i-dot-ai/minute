'use client'

import React, { useEffect, useMemo, useRef, useState } from 'react'

interface MinuteVisualizerProps {
  stream: MediaStream | null
  isRecording: boolean
  isPaused?: boolean
  /** Fired once when sustained silence starts/ends, for a11y announcements. */
  onSilenceChange?: (silent: boolean) => void
}

// Bar geometry in real pixels (3px bars on a 12px pitch). The viewBox is sized
// to the container so these stay the same width at any screen size — a wider
// container gets more bars rather than wider ones.
const PITCH = 12
const BAR_WIDTH = 3
const BAR_RADIUS = 1.5

const VIEW_HEIGHT = 200
const CENTER_Y = VIEW_HEIGHT / 2
// Bars rest as short stubs rather than collapsing away, so the row stays
// readable as a row when a band drops out.
const MIN_HEIGHT = 4
const MAX_HEIGHT = VIEW_HEIGHT * 0.95
// Speech rarely fills a band to full scale, so lift levels to use the height
// available. Matches the multiplier the previous canvas visualiser used.
const GAIN = 1.2

// Below this average byte value we treat the mic as quiet and show the dot.
const SILENCE_LEVEL = 8
// Sustained quiet before we flag silence, so natural speech pauses don't trip it.
const SILENCE_MS = 3000
// Both of these damp single-frame flicker. Keep them low: the point of the
// visualiser is to show the user their voice is being picked up, which it can
// only do if the bars track the audio closely.
const SMOOTHING = 0.5
const TWEEN = 0.5

const lerp = (from: number, to: number, t: number) => from + (to - from) * t
const clamp = (v: number, min: number, max: number) =>
  Math.max(min, Math.min(max, v))

/** Evenly spaced bar positions filling `width`, centred as a block. */
function buildBars(width: number): number[] {
  if (width <= 0) return []

  const count = Math.max(5, Math.floor(width / PITCH))
  const span = count * PITCH - (PITCH - BAR_WIDTH)
  const startX = (width - span) / 2

  return Array.from({ length: count }, (_, i) => startX + i * PITCH)
}

/**
 * Audio visualiser: thin bars whose heights track the microphone's frequency
 * spectrum, bass on the left through treble on the right. When there's no sound
 * (quiet, paused, or no stream) the bars fade out and a single pulsing dot takes
 * their place.
 *
 * Decorative only (aria-hidden) — the recording UI owns status announcements.
 */
export default function MinuteVisualizer({
  stream,
  isRecording,
  isPaused = false,
  onSilenceChange,
}: MinuteVisualizerProps) {
  const wrapperRef = useRef<HTMLDivElement>(null)
  const rectsRef = useRef<(SVGRectElement | null)[]>([])
  const barsGroupRef = useRef<SVGGElement | null>(null)
  const dotRef = useRef<SVGCircleElement | null>(null)
  const animationRef = useRef<number | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const dataArrayRef = useRef<Uint8Array | null>(null)

  const [width, setWidth] = useState(0)
  const bars = useMemo(() => buildBars(width), [width])

  // Mirrored for the rAF loop, which must not restart when the bars change.
  const barsRef = useRef<number[]>(bars)
  barsRef.current = bars

  // Current animated heights, tweened toward their targets each frame.
  const heightsRef = useRef<number[]>([])
  // Cross-fade between the bars and the dot (1 = bars, 0 = dot).
  const barsMixRef = useRef(0)

  const silenceStartRef = useRef<number | null>(null)
  const silentRef = useRef(false)
  const onSilenceChangeRef = useRef(onSilenceChange)
  onSilenceChangeRef.current = onSilenceChange

  // Track the container width so the bar count follows the available space.
  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return undefined

    const update = () => setWidth(el.getBoundingClientRect().width)
    update()

    const observer = new ResizeObserver(update)
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    silenceStartRef.current = null

    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

    const isValidStream =
      stream && stream.active && stream.getAudioTracks().length > 0

    const teardownAudio = () => {
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(console.error)
        audioContextRef.current = null
      }
      analyserRef.current = null
      dataArrayRef.current = null
    }

    if (isValidStream && isRecording) {
      try {
        teardownAudio()
        const audioContext = new AudioContext()
        const analyser = audioContext.createAnalyser()
        // 1024 gives 512 bins (256 usable), enough resolution that each bar
        // covers a distinct band even at wide container widths.
        analyser.fftSize = 1024
        analyser.smoothingTimeConstant = SMOOTHING

        dataArrayRef.current = new Uint8Array(analyser.frequencyBinCount)
        audioContext.createMediaStreamSource(stream).connect(analyser)

        audioContextRef.current = audioContext
        analyserRef.current = analyser
      } catch (error) {
        console.error('Error setting up audio context', error)
      }
    }

    const setSilent = (silent: boolean) => {
      if (silentRef.current === silent) return
      silentRef.current = silent
      onSilenceChangeRef.current?.(silent)
    }

    const draw = () => {
      const currentBars = barsRef.current
      const barCount = currentBars.length

      // Re-seed the tween buffer when the bar count changes on resize.
      if (heightsRef.current.length !== barCount) {
        heightsRef.current = new Array(barCount).fill(MIN_HEIGHT)
      }

      const analyser = analyserRef.current
      const dataArray = dataArrayRef.current

      let showBars = false
      if (barCount > 0 && analyser && dataArray && isRecording && !isPaused) {
        analyser.getByteFrequencyData(dataArray)

        const average =
          dataArray.reduce((sum, v) => sum + v, 0) / dataArray.length
        const hasAudio = average > SILENCE_LEVEL
        showBars = hasAudio

        if (hasAudio) {
          silenceStartRef.current = null
          setSilent(false)
        } else {
          silenceStartRef.current ??= Date.now()
          if (Date.now() - silenceStartRef.current > SILENCE_MS) {
            setSilent(true)
          }
        }

        if (hasAudio) {
          // Spread the bars across the usable (lower) half of the spectrum so
          // each one shows its own band: bass on the left, treble on the right.
          const usable = Math.floor(dataArray.length / 2)
          for (let i = 0; i < barCount; i += 1) {
            const from = Math.floor((i / barCount) * usable)
            const to = Math.max(
              from + 1,
              Math.floor(((i + 1) / barCount) * usable)
            )
            let sum = 0
            for (let j = from; j < to; j += 1) sum += dataArray[j] ?? 0
            const level = sum / (to - from) / 255

            const target = clamp(
              level * GAIN * MAX_HEIGHT,
              MIN_HEIGHT,
              MAX_HEIGHT
            )
            heightsRef.current[i] = prefersReducedMotion
              ? target
              : lerp(heightsRef.current[i], target, TWEEN)
          }
        }
      } else {
        silenceStartRef.current = null
      }

      // Ease heights back down to stubs when idle.
      if (!showBars) {
        for (let i = 0; i < barCount; i += 1) {
          heightsRef.current[i] = prefersReducedMotion
            ? MIN_HEIGHT
            : lerp(heightsRef.current[i], MIN_HEIGHT, 0.2)
        }
      }

      // Cross-fade bars <-> dot.
      const mixTarget = showBars ? 1 : 0
      barsMixRef.current = prefersReducedMotion
        ? mixTarget
        : lerp(barsMixRef.current, mixTarget, 0.12)
      const barsMix = barsMixRef.current

      for (let i = 0; i < barCount; i += 1) {
        const rect = rectsRef.current[i]
        if (!rect) continue
        const h = heightsRef.current[i]
        rect.setAttribute('height', h.toFixed(2))
        rect.setAttribute('y', (CENTER_Y - h / 2).toFixed(2))
      }
      barsGroupRef.current?.setAttribute('opacity', barsMix.toFixed(3))

      const dot = dotRef.current
      if (dot) {
        const pulse = prefersReducedMotion
          ? 0
          : Math.sin((Date.now() / 1000) * 2) * 1.5
        dot.setAttribute('r', (7 + pulse).toFixed(2))
        dot.setAttribute('opacity', (1 - barsMix).toFixed(3))
      }

      animationRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
        animationRef.current = null
      }
      // Stopping or pausing isn't silence worth announcing — clear any flag so
      // the next run starts clean.
      setSilent(false)
      teardownAudio()
    }
  }, [stream, isRecording, isPaused])

  return (
    <div ref={wrapperRef} className="w-full">
      {width > 0 && (
        <svg
          viewBox={`0 0 ${width} ${VIEW_HEIGHT}`}
          preserveAspectRatio="none"
          aria-hidden="true"
          focusable="false"
          role="presentation"
          className="h-[200px] w-full"
        >
          <g ref={barsGroupRef} opacity={0}>
            {/* Baseline — hairline */}
            <line
              x1={0}
              y1={CENTER_Y}
              x2={width}
              y2={CENTER_Y}
              stroke="rgba(29,112,184,0.15)"
              strokeWidth={0.75}
            />
            {bars.map((x, i) => (
              <rect
                // eslint-disable-next-line react/no-array-index-key
                key={i}
                ref={(el) => {
                  rectsRef.current[i] = el
                }}
                x={x}
                width={BAR_WIDTH}
                rx={BAR_RADIUS}
                y={CENTER_Y - MIN_HEIGHT / 2}
                height={MIN_HEIGHT}
                fill="#1d70b8"
              />
            ))}
          </g>

          <circle
            ref={dotRef}
            cx={width / 2}
            cy={CENTER_Y}
            r={7}
            opacity={0}
            fill="#1d70b8"
          />
        </svg>
      )}
    </div>
  )
}
