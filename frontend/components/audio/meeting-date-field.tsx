'use client'

import { TranscriptionForm } from '@/components/audio/types'
import { useFormContext } from 'react-hook-form'

// YYYY-MM-DD in local time (not UTC), as used by <input type="date">.
export const toLocalIsoDate = (date: Date = new Date()) => {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
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
        max={toLocalIsoDate()}
        aria-describedby="meeting-date-hint"
        {...form.register('meeting_date')}
      />
    </div>
  )
}
