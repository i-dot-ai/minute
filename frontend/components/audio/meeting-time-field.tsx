'use client'

import { TranscriptionForm } from '@/components/audio/types'
import { measureAudioDurationSec } from '@/lib/recording-duration'
import { useState } from 'react'
import { useController, useFormContext } from 'react-hook-form'

// When the meeting started, as typed. Kept as separate strings so partial
// entries survive re-renders; toApiMeetingDatetime turns it into an ISO string.
export type MeetingTime = {
  day: string
  month: string
  year: string
  time: string
}

const pad = (n: number) => String(n).padStart(2, '0')

export const toMeetingTime = (date: Date): MeetingTime => ({
  day: String(date.getDate()),
  month: String(date.getMonth() + 1),
  year: String(date.getFullYear()),
  time: `${pad(date.getHours())}:${pad(date.getMinutes())}`,
})

// The browser only knows when an uploaded file was last saved, which for a
// recording is usually when it ended, so take off its length to get the start.
// Without a length we only trust the day, and leave the time for the user.
export const guessUploadMeetingTime = async (
  file: File
): Promise<MeetingTime> => {
  const savedAt = new Date(file.lastModified)
  const durationSec = await measureAudioDurationSec(file)
  if (durationSec === null) return { ...toMeetingTime(savedAt), time: '' }
  return toMeetingTime(new Date(savedAt.getTime() - durationSec * 1000))
}

// Accepts "14:30", "14.30", "2:30pm", "2pm" and "2.30 p.m.", so nobody needs
// to know the 24-hour clock.
const parseTime = (value: string) => {
  const match = value
    .trim()
    .toLowerCase()
    .match(/^(\d{1,2})(?:[:.](\d{2}))?\s*([ap])?\.?\s*(?:m\.?)?$/)
  if (!match) return null
  const [, h, m, period] = match
  let hours = Number(h)
  const minutes = m ? Number(m) : 0
  if (minutes > 59) return null
  if (period) {
    if (hours < 1 || hours > 12) return null
    hours = (hours % 12) + (period === 'p' ? 12 : 0)
  } else if (!m || hours > 23) {
    // "14" on its own is too ambiguous to guess at.
    return null
  }
  return { hours, minutes }
}

const toDate = ({ day, month, year, time }: MeetingTime) => {
  const parsed = parseTime(time)
  if (!parsed) return null
  const date = new Date(
    Number(year),
    Number(month) - 1,
    Number(day),
    parsed.hours,
    parsed.minutes
  )
  return date.getFullYear() === Number(year) &&
    date.getMonth() === Number(month) - 1 &&
    date.getDate() === Number(day)
    ? date
    : null
}

// Error messages follow the GOV.UK date input guidance.
export const validateMeetingTime = (value?: MeetingTime): true | string => {
  const { day = '', month = '', year = '', time = '' } = value ?? {}
  if (!day && !month && !year && !time) {
    return 'Enter when the meeting started'
  }
  const missing = [!day && 'day', !month && 'month', !year && 'year'].filter(
    Boolean
  )
  if (missing.length) {
    return `Meeting date must include a ${missing.join(' and ')}`
  }
  if (year.length !== 4) return 'Year must include 4 numbers'
  if (!time) return 'Enter the time the meeting started'
  if (!parseTime(time)) {
    return 'Enter the time in the format 14:30 or 2:30pm'
  }
  const date = toDate({ day, month, year, time })
  if (!date) return 'Meeting date must be a real date'
  if (date > new Date()) return 'Meeting start time must be in the past'
  return true
}

export const toApiMeetingDatetime = (value?: MeetingTime) =>
  value && validateMeetingTime(value) === true
    ? toDate(value)?.toISOString()
    : undefined

export const formatMeetingTime = (date: Date) =>
  `${date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })}, ${pad(date.getHours())}:${pad(date.getMinutes())}`

const DATE_FIELDS = [
  { part: 'day', label: 'Day', width: 2 },
  { part: 'month', label: 'Month', width: 2 },
  { part: 'year', label: 'Year', width: 4 },
] as const

export const MeetingTimeField = ({
  startEditing = false,
}: {
  startEditing?: boolean
}) => {
  const { clearErrors } = useFormContext<TranscriptionForm>()
  const { field, fieldState } = useController<
    TranscriptionForm,
    'meeting_datetime'
  >({
    name: 'meeting_datetime',
    rules: { validate: validateMeetingTime },
  })
  // Most people only need to check the pre-filled time, so show it as one line
  // and open the boxes on "Change", or straight away if there's nothing to show.
  const [editing, setEditing] = useState(startEditing)
  const value = field.value ?? { day: '', month: '', year: '', time: '' }
  const error = fieldState.error?.message

  const setPart = (part: keyof MeetingTime, input: string) => {
    if (error) clearErrors('meeting_datetime')
    // Keep the boxes open once the user has typed, even when the value becomes valid.
    setEditing(true)
    field.onChange({
      ...value,
      [part]: part === 'time' ? input : input.replace(/\D/g, ''),
    })
  }

  if (!editing && validateMeetingTime(value) === true) {
    return (
      <div className="govuk-form-group">
        <p className="govuk-body govuk-!-margin-bottom-0">
          <span className="govuk-!-font-weight-bold">Meeting started:</span>{' '}
          {formatMeetingTime(toDate(value)!)} ·{' '}
          <button
            type="button"
            className="govuk-link text-(--govuk-link-colour) hover:cursor-pointer"
            onClick={() => setEditing(true)}
          >
            Change
            <span className="govuk-visually-hidden"> meeting start time</span>
          </button>
        </p>
      </div>
    )
  }

  return (
    <div
      className={`govuk-form-group ${error ? 'govuk-form-group--error' : ''}`}
    >
      <fieldset
        className="govuk-fieldset"
        role="group"
        aria-describedby={error ? 'meeting-time-error' : undefined}
      >
        <legend className="govuk-fieldset__legend">
          When did the meeting start?
        </legend>
        {error && (
          <p id="meeting-time-error" className="govuk-error-message">
            <span className="govuk-visually-hidden">Error:</span> {error}
          </p>
        )}
        <div className="govuk-date-input">
          {DATE_FIELDS.map(({ part, label, width }) => (
            <div className="govuk-date-input__item" key={part}>
              <div className="govuk-form-group">
                <label
                  className="govuk-label govuk-date-input__label"
                  htmlFor={`meeting-date-${part}`}
                >
                  {label}
                </label>
                <input
                  className={`govuk-input govuk-input--subtle govuk-date-input__input govuk-input--width-${width} ${error ? 'govuk-input--error' : ''}`}
                  id={`meeting-date-${part}`}
                  type="text"
                  inputMode="numeric"
                  value={value[part]}
                  onChange={(e) => setPart(part, e.target.value)}
                  onBlur={field.onBlur}
                />
              </div>
            </div>
          ))}
          <div className="govuk-date-input__item">
            <div className="govuk-form-group">
              <label
                className="govuk-label govuk-date-input__label"
                htmlFor="meeting-time"
              >
                Time
              </label>
              <input
                className={`govuk-input govuk-input--subtle govuk-date-input__input govuk-input--width-5 ${error ? 'govuk-input--error' : ''}`}
                id="meeting-time"
                type="text"
                autoComplete="off"
                value={value.time}
                onChange={(e) => setPart('time', e.target.value)}
                onBlur={field.onBlur}
              />
            </div>
          </div>
        </div>
      </fieldset>
    </div>
  )
}
