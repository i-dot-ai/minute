export type StatusBucket = {
  start: string
  completed: number
  failed: number
  failure_rate: number | null
  avg_processing_seconds: number | null
  audio_hours: number
  projected_one_hour_seconds: number | null
}

export type HourlyProcessingStatus = {
  partial: boolean
  hours: StatusBucket[]
  last_10_minutes: StatusBucket
  collected_at: string
}

// Alert limits, judged on the last-10-minute transcription of transcriptions which is often between 3-10
// Below 5 transcriptions in that 10 miins you need at least 3 failures to trigger the banner and status of high failures
// Above 5 transcriptions in the 10 mins and you need at least 50% failure rate
// Long processing times requires processing times to go above 10 mins - usually around 1-4 mins
const MIN_FAILURES = 3
const MIN_OUTCOMES = 5
const FAILURE_RATE = 0.5
const SLOW_PROJECTED_SECONDS = 600

export function processingAlert(recent: StatusBucket | undefined) {
  const failing =
    !!recent &&
    recent.failed >= MIN_FAILURES &&
    (recent.completed + recent.failed < MIN_OUTCOMES ||
      (recent.failure_rate ?? 0) > FAILURE_RATE)
  const slow =
    (recent?.projected_one_hour_seconds ?? 0) > SLOW_PROJECTED_SECONDS
  const systemStatusTitle = failing
    ? slow
      ? 'We are currently experiencing a high number of failed transcripts and long processing times'
      : 'We are currently experiencing a high number of failed transcripts'
    : slow
      ? 'We are currently experiencing long processing times'
      : ''
  return { failing, slow, systemStatusTitle }
}
