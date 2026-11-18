import { Template } from '@/types/templates'

export type TranscriptionForm = {
  file: Blob | File | null
  template: Template
  agenda?: string
  // As typed in the date input; send it with toApiMeetingDate. Never guessed:
  // blank for uploads, the recording's own date for live and incomplete ones.
  meeting_date?: string
  recordingId?: string
}
