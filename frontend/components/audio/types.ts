import { TranscriptionCreateRequest } from '@/lib/client'
import { Template } from '@/types/templates'

export type TranscriptionForm = {
  file: Blob | File | null
  template: Template
  language: TranscriptionCreateRequest['language']
  agenda?: string
  recordingId?: string
}
