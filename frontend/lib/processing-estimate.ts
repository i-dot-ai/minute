// Processing normally takes 1.5 minutes per hour of audio.
// Generating the summary takes about as long as the transcription.
// The two together come to 2 minutes per hour of audio.
const TRANSCRIPTION_MINUTES_PER_AUDIO_MINUTE = 0.017
const SUMMARY_MINUTES_PER_AUDIO_MINUTE = 0.017

// Short recordings still carry fixed overheads, so never estimate below this.
const MINIMUM_ESTIMATE_MINUTES = 1

// A phase counts as stalled once it has run twice as long as its estimate.
// Short clips get a floor so a quick job is not flagged seconds after its
// estimate lapses, and an unknown duration falls back to a flat limit.
const STALL_ESTIMATE_MULTIPLIER = 2
const TRANSCRIPTION_STALL_FLOOR_MINUTES = 3
const SUMMARY_STALL_FLOOR_MINUTES = 3
const STALL_FALLBACK_MINUTES = 10

const MS_PER_MINUTE = 60 * 1000

export type ProcessingPhase = 'transcription' | 'summary'

const getEstimateMinutes = (
  durationSec: number | null,
  minutesPerAudioMinute: number
) =>
  durationSec
    ? Math.max(
        MINIMUM_ESTIMATE_MINUTES,
        Math.round((durationSec / 60) * minutesPerAudioMinute)
      )
    : null

/** Transcribing the audio and then generating the first summary from it. */
export const getTotalEstimateMinutes = (durationSec: number | null) =>
  getEstimateMinutes(
    durationSec,
    TRANSCRIPTION_MINUTES_PER_AUDIO_MINUTE + SUMMARY_MINUTES_PER_AUDIO_MINUTE
  )

/** Generating a summary from a transcript that already exists. */
export const getSummaryEstimateMinutes = (durationSec: number | null) =>
  getEstimateMinutes(durationSec, SUMMARY_MINUTES_PER_AUDIO_MINUTE)

const getStallLimitMs = (
  durationSec: number | null,
  phase: ProcessingPhase
) => {
  const estimateMinutes =
    phase === 'summary'
      ? getSummaryEstimateMinutes(durationSec)
      : getTotalEstimateMinutes(durationSec)
  if (!estimateMinutes) return STALL_FALLBACK_MINUTES * MS_PER_MINUTE
  const floorMinutes =
    phase === 'summary'
      ? SUMMARY_STALL_FLOOR_MINUTES
      : TRANSCRIPTION_STALL_FLOOR_MINUTES
  return (
    Math.max(floorMinutes, estimateMinutes * STALL_ESTIMATE_MULTIPLIER) *
    MS_PER_MINUTE
  )
}

const getElapsedMs = (startedAt: string, now: number | null) =>
  now === null ? 0 : now - new Date(startedAt).getTime()

/**
 * Minutes left of `estimateMinutes`, counted from `startedAt` rather than held
 * in state so the figure survives reloads and backgrounded tabs. Never counts
 * below `minimumMinutes`, which the transcription phase uses to hold back the
 * time the summary still needs once transcription is done.
 */
export const getRemainingMinutes = ({
  startedAt,
  estimateMinutes,
  minimumMinutes = 0,
  now,
}: {
  startedAt: string | null | undefined
  estimateMinutes: number | null
  minimumMinutes?: number | null
  now: number | null
}) => {
  if (!startedAt || !estimateMinutes) return null
  const elapsedMinutes = getElapsedMs(startedAt, now) / MS_PER_MINUTE
  return Math.max(
    minimumMinutes ?? 0,
    Math.ceil(estimateMinutes - elapsedMinutes)
  )
}

/** Whether a phase has been running long enough to warn the user about it. */
export const getIsStalled = ({
  startedAt,
  durationSec,
  phase,
  now,
}: {
  startedAt: string | null | undefined
  durationSec: number | null
  phase: ProcessingPhase
  now: number | null
}) =>
  !!startedAt &&
  getElapsedMs(startedAt, now) > getStallLimitMs(durationSec, phase)
