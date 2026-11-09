import type { TranscriptionErrorCode } from '@/lib/client/types.gen'

export function getTranscriptionErrorMessage(
  errorCode?: TranscriptionErrorCode | null
): string {
  if (errorCode === 'no_speech_detected') {
    return 'No speech was detected in this recording. The microphone may have been muted or the meeting may have been silent. If you believe this is a mistake, '
  }
  return 'There was an internal server error. Please try again. If the issue persists, '
}
