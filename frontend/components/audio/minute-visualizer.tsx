'use client'

import React, { useEffect, useRef } from 'react'

interface MinuteVisualizerProps {
  stream: MediaStream | null
  isRecording: boolean
  isPaused?: boolean
  /** Fired once when sustained silence starts/ends, for a11y announcements. */
  onSilenceChange?: (silent: boolean) => void
}

// Geometry lifted from public/images/minute-icon-waveform.svg: 21 thin bars,
// symmetric around the centre, all centred vertically on y = 80, with a fixed
// opacity that fades outward. [x, restHeight, opacity]
const BARS: [number, number, number][] = [
  [10, 20, 0.12],
  [22, 30, 0.18],
  [34, 44, 0.25],
  [46, 56, 0.32],
  [58, 40, 0.38],
  [70, 72, 0.48],
  [82, 50, 0.55],
  [94, 88, 0.65],
  [106, 64, 0.75],
  [118, 116, 0.88],
  [128.5, 136, 1], // centre peak
  [139, 116, 0.88],
  [151, 64, 0.75],
  [163, 88, 0.65],
  [175, 50, 0.55],
  [187, 72, 0.48],
  [199, 40, 0.38],
  [211, 56, 0.32],
  [223, 44, 0.25],
  [235, 30, 0.18],
  [247, 20, 0.12],
]
const BAR_WIDTH = 3
const BAR_RADIUS = 1.5
const BAR_COUNT = BARS.length
const CENTER_Y = 80
const CENTER_X = 130
const MAX_HEIGHT = 152 // stay inside the 160-tall viewBox

// Below this average byte value we treat the mic as quiet and show the dot.
const SILENCE_LEVEL = 8
// Sustained quiet before we flag silence, so natural speech pauses don't trip it.
const SILENCE_MS = 3000

const lerp = (from: number, to: number, t: number) => from + (to - from) * t
const clamp = (v: number, min: number, max: number) =>
  Math.max(min, Math.min(max, v))

/**
 * Audio visualiser styled like the minute waveform mark: 21 thin bars,
 * symmetric with a dominant centre peak, driven by the mic's frequency data.
 * When there's no sound (quiet, paused, or no stream) the bars fade out and a
 * single pulsing dot takes their place.
 *
 * Decorative only (aria-hidden) — the recording UI owns status announcements.
 */
export default function MinuteVisualizer({
  stream,
  isRecording,
  isPaused = false,
  onSilenceChange,
}: MinuteVisualizerProps) {
  const rectsRef = useRef<(SVGRectElement | null)[]>([])
  const barsGroupRef = useRef<SVGGElement | null>(null)
  const dotRef = useRef<SVGCircleElement | null>(null)
  const animationRef = useRef<number | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const dataArrayRef = useRef<Uint8Array | null>(null)

  // Current animated heights, tweened toward their targets each frame.
  const heightsRef = useRef<number[]>(BARS.map(([, h]) => h))
  // Cross-fade between the bars and the dot (1 = bars, 0 = dot).
  const barsMixRef = useRef(0)

  const silenceStartRef = useRef<number | null>(null)
  const silentRef = useRef(false)
  const onSilenceChangeRef = useRef(onSilenceChange)
  onSilenceChangeRef.current = onSilenceChange

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
        analyser.fftSize = 256
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
      const analyser = analyserRef.current
      const dataArray = dataArrayRef.current

      let showBars = false
      if (analyser && dataArray && isRecording && !isPaused) {
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
          // Downsample the usable (lower) half of the spectrum into 21 buckets,
          // then mirror around the centre so it stays symmetric like the mark.
          const usable = Math.floor(dataArray.length / 2)
          const bucketSize = Math.max(1, Math.floor(usable / BAR_COUNT))
          const raw = new Array(BAR_COUNT).fill(0)
          for (let i = 0; i < BAR_COUNT; i += 1) {
            let sum = 0
            for (let j = 0; j < bucketSize; j += 1) {
              sum += dataArray[i * bucketSize + j] ?? 0
            }
            raw[i] = sum / bucketSize / 255
          }

          for (let i = 0; i < BAR_COUNT; i += 1) {
            const level = (raw[i] + raw[BAR_COUNT - 1 - i]) / 2
            const rest = BARS[i][1]
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
        for (let i = 0; i < BAR_COUNT; i += 1) {
          heightsRef.current[i] = prefersReducedMotion
            ? BARS[i][1]
            : lerp(heightsRef.current[i], BARS[i][1], 0.2)
        }
      }

      // Cross-fade bars <-> dot.
      const mixTarget = showBars ? 1 : 0
      barsMixRef.current = prefersReducedMotion
        ? mixTarget
        : lerp(barsMixRef.current, mixTarget, 0.12)
      const barsMix = barsMixRef.current

      for (let i = 0; i < BAR_COUNT; i += 1) {
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
        dot.setAttribute('r', (6 + pulse).toFixed(2))
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
    <svg
      viewBox="0 0 260 160"
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
      focusable="false"
      role="presentation"
    >
      {/* Transparent background — blue bars sit on whatever's behind. */}
      <g ref={barsGroupRef} opacity={0}>
        {/* Baseline — hairline */}
        <line
          x1={10}
          y1={CENTER_Y}
          x2={250}
          y2={CENTER_Y}
          stroke="rgba(29,112,184,0.15)"
          strokeWidth={0.75}
        />
        {BARS.map(([x, h, opacity], i) => (
          <rect
            // eslint-disable-next-line react/no-array-index-key
            key={i}
            ref={(el) => {
              rectsRef.current[i] = el
            }}
            x={x}
            width={BAR_WIDTH}
            rx={BAR_RADIUS}
            y={CENTER_Y - h / 2}
            height={h}
            fill={`rgba(29,112,184,${opacity})`}
          />
        ))}
      </g>

      <circle cx={CENTER_X} cy={CENTER_Y} r={6} opacity={0} fill="#1d70b8" ref={dotRef} />
    </svg>
  )
}
