import { Template } from '@/types/templates'

import { MeetingTime } from './meeting-time-field'

export type TranscriptionForm = {
  file: Blob | File | null
  template: Template
  agenda?: string
  // When the meeting started; send it with toApiMeetingDatetime. Pre-filled
  // from the file for uploads; recordings use the time recording started.
  meeting_datetime?: MeetingTime
  recordingId?: string
}
