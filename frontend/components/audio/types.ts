import { Template } from '@/types/templates'

import { MeetingTime } from './meeting-time-field'

export type TranscriptionForm = {
  file: Blob | File | null
  template: Template
  agenda?: string
  meeting_datetime?: MeetingTime
  recordingId?: string
}
