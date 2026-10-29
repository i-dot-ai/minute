// Only the aggregate fields used by the home-page panel.
export type ProcessingStatus = {
  horizon_seconds: number
  components: {
    transcription: {
      counts: { completed: number }
      failure_rate: number | null
      processing_time_seconds: {
        p50: number | null
        p90: number | null
        p99: number | null
      }
    }
  }
}
