'use client'

import { TranscriptionForm } from '@/components/audio/types'
import { useFormContext } from 'react-hook-form'

// Local (not UTC) date, so the max is today wherever the user is.
const todayIsoDate = () => {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

export const MeetingDateField = () => {
  const form = useFormContext<TranscriptionForm>()
  return (
    <div className="govuk-form-group">
      <label className="govuk-label" htmlFor="meeting_date">
        Meeting date (optional)
      </label>
      <div id="meeting-date-hint" className="govuk-hint">
        Used in the summary. If you leave this blank, the summary will say the
        date was not provided.
      </div>
      <input
        className="govuk-input govuk-input--width-10"
        id="meeting_date"
        type="date"
        max={todayIsoDate()}
        aria-describedby="meeting-date-hint"
        {...form.register('meeting_date')}
      />
    </div>
  )
}
