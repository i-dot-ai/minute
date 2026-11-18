import { Template } from '@/types/templates'

export type TranscriptionForm = {
  file: Blob | File | null
  template: Template
  agenda?: string
  // YYYY-MM-DD, only ever entered by the user: never default it.
  meeting_date?: string
  recordingId?: string
}
