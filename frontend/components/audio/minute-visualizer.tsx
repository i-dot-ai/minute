'use client'

import React, { useEffect, useMemo, useRef, useState } from 'react'

interface MinuteVisualizerProps {
  stream: MediaStream | null
  isRecording: boolean
  isPaused?: boolean
  /** Fired once when sustained silence starts/ends, for a11y announcements. */
  onSilenceChange?: (silent: boolean) => void
}

// Bar geometry in real pixels, matching public/images/minute-icon-waveform.svg
// (3px bars on a 12px pitch). The viewBox is sized to the container so these
// stay the same width at any screen size — a wider container gets more bars
// rather than wider ones.
const PITCH = 12
const BAR_WIDTH = 3
const BAR_RADIUS = 1.5

const VIEW_HEIGHT = 200
const CENTER_Y = VIEW_HEIGHT / 2
// Height profile. Exaggerated relative to the reference mark so the tall/short
// contrast reads as the minute silhouette rather than a flat spectrum.
const PEAK_HEIGHT = VIEW_HEIGHT * 0.9
// A high floor keeps the outer bars substantial so the waveform reads fairly
// evenly across its width, still peaking in the middle but not collapsing.
const MIN_HEIGHT = VIEW_HEIGHT * 0.3
const MAX_HEIGHT = VIEW_HEIGHT * 0.95
// Envelope shape. A super-Gaussian keeps the whole middle section standing tall
// and drops away sharply toward the edges, rather than tapering evenly.
// Higher = middle section stands further above the outer bars.
const CENTRE_FOCUS = 1.6
// Higher = flatter, broader middle with a sharper falloff at the edges.
const FOCUS_POWER = 2.5
// Every other bar out from the centre dips, as in the reference mark. This is
// surface texture only — the tall/short contrast comes from the envelope above.
const ZIGZAG_DIP = 0.72

// Below this average byte value we treat the mic as quiet and show the dot.
const SILENCE_LEVEL = 8
// Sustained quiet before we flag silence, so natural speech pauses don't trip it.
const SILENCE_MS = 3000

interface Bar {
  x: number
  /** Resting height — the shape the waveform settles into when idle. */
  h: number
  opacity: number
}

const lerp = (from: number, to: number, t: number) => from + (to - from) * t
const clamp = (v: number, min: number, max: number) =>
  Math.max(min, Math.min(max, v))

/**
 * Builds a symmetric, centre-peaked bar set to fill `width`, reproducing the
 * reference mark's profile: a smooth falloff from the centre, a zigzag where
 * every other bar dips, and opacity fading outward.
 */
function buildBars(width: number): Bar[] {
  if (width <= 0) return []

  // Odd count so there's a true centre bar to peak on.
  let count = Math.max(5, Math.floor(width / PITCH))
  if (count % 2 === 0) count -= 1

  const mid = (count - 1) / 2
  const span = count * PITCH - (PITCH - BAR_WIDTH)
  const startX = (width - span) / 2

  return Array.from({ length: count }, (_, i) => {
    const d = Math.abs(i - mid)
    const t = mid === 0 ? 0 : d / mid
    const envelope = Math.exp(-CENTRE_FOCUS * t ** FOCUS_POWER)
    let h = MIN_HEIGHT + (PEAK_HEIGHT - MIN_HEIGHT) * envelope
    // Every other bar out from the centre dips, as in the reference mark.
    if (d >= 2 && d % 2 === 0) h *= ZIGZAG_DIP
    return { x: startX + i * PITCH, h, opacity: 1 - 0.88 * t }
  })
}

/**
 * Audio visualiser styled like the minute waveform mark: thin bars, symmetric
 * with a dominant centre peak, driven by the mic's frequency data. When there's
 * no sound (quiet, paused, or no stream) the bars fade out and a single pulsing
 * dot takes their place.
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
  const barsRef = useRef<Bar[]>(bars)
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
        analyser.smoothingTimeConstant = 0.7

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
        heightsRef.current = currentBars.map((bar) => bar.h)
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

            const rest = currentBars[i].h
            // Keep the silhouette (taller bars stay taller) but let audio push
            // each bar up and down around its resting height.
            const target = clamp(
              rest * (0.5 + level * 1.2),
              rest * 0.45,
              Math.min(MAX_HEIGHT, rest * 1.7)
            )
            heightsRef.current[i] = prefersReducedMotion
              ? target
              : lerp(heightsRef.current[i], target, 0.35)
          }
        }
      } else {
        silenceStartRef.current = null
      }

      // Ease heights back to the resting waveform silhouette when idle.
      if (!showBars) {
        for (let i = 0; i < barCount; i += 1) {
          heightsRef.current[i] = prefersReducedMotion
            ? currentBars[i].h
            : lerp(heightsRef.current[i], currentBars[i].h, 0.2)
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
            {bars.map((bar, i) => (
              <rect
                // eslint-disable-next-line react/no-array-index-key
                key={i}
                ref={(el) => {
                  rectsRef.current[i] = el
                }}
                x={bar.x}
                width={BAR_WIDTH}
                rx={BAR_RADIUS}
                y={CENTER_Y - bar.h / 2}
                height={bar.h}
                fill={`rgba(29,112,184,${bar.opacity.toFixed(3)})`}
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
