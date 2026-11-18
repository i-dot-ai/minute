import { Template } from '@/types/templates'

export type TranscriptionForm = {
  file: Blob | File | null
  template: Template
  agenda?: string
  // YYYY-MM-DD. Never guessed: blank for uploads, the recording's own date for
  // live and incomplete recordings.
  meeting_date?: string
  recordingId?: string
}
