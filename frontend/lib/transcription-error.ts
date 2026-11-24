export const NO_SPEECH_MESSAGE =
  'No speech detected. Please check that the recording is not silent and contains speech. If you think this is an error, please '

export function getTranscriptionErrorMessage(): string {
  return 'There was an internal server error. Please try again. If the issue persists, '
}
