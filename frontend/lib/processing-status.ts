export type StatusBucket = {
  start: string
  completed: number
  failed: number
  failure_rate: number | null
  avg_processing_seconds: number | null
  audio_hours: number
  processing_seconds_per_audio_hour: number | null
  per_audio_hour_seconds: {
    sample_count: number
    p50: number | null
    p90: number | null
    p99: number | null
  }
}

export type HourlyProcessingStatus = {
  partial: boolean
  hours: StatusBucket[]
  last_10_minutes: StatusBucket
}
