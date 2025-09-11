export type TranscriptionForm = {
  file: Blob | File | null
  template: string
  agenda?: string
  recordingId?: string
}
