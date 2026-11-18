import { Template } from '@/types/templates'

export type TranscriptionForm = {
  file: Blob | File | null
  template: Template
  agenda?: string
  // As typed in the date input; send it with toApiMeetingDate. Defaults to
  // today for uploads; live and incomplete recordings use their own date.
  meeting_date?: string
  recordingId?: string
}
