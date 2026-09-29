// Temporary function until logging returns usable errors.
// Therefore acceptable to rely on flaky string message from API for now.

export function getTranscriptionErrorMessage(error?: string | null): string {
  if (error && error.includes('No transcription phrases found')) {
    return 'No usable audio detected. The recording may be silent or too short.'
  }
  return 'There was an internal server error. Please try again.'
}
