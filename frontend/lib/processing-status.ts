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
}
