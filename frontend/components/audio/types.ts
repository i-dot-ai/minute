import { Template } from '@/types/templates'

export type TranscriptionForm = {
  file: Blob | File | null
  template: Template
  agenda?: string
  recordingId?: string
}
