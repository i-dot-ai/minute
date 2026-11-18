'use client'

import { TranscriptionForm } from '@/components/audio/types'
import { useController, useFormContext } from 'react-hook-form'

// YYYY-MM-DD in local time (not UTC).
export const toLocalIsoDate = (date: Date = new Date()) => {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

type DateParts = { day: string; month: string; year: string }

// The form holds the date as typed ("year-month-day", unpadded) so partial
// entries survive re-renders. toApiMeetingDate turns it into YYYY-MM-DD.
const splitDate = (value?: string): DateParts => {
  const [year = '', month = '', day = ''] = (value ?? '').split('-')
  return { day, month, year }
}

const joinDate = ({ day, month, year }: DateParts) =>
  day || month || year ? `${year}-${month}-${day}` : ''

const toIsoDate = ({ day, month, year }: DateParts) =>
  `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`

// Error messages follow the GOV.UK date input guidance.
export const validateMeetingDate = (value?: string): true | string => {
  const parts = splitDate(value)
  const { day, month, year } = parts
  if (!day && !month && !year) return true

  const missing = [!day && 'day', !month && 'month', !year && 'year'].filter(
    Boolean
  )
  if (missing.length) {
    return `Meeting date must include a ${missing.join(' and ')}`
  }
  if (year.length !== 4) return 'Year must include 4 numbers'

  const date = new Date(Number(year), Number(month) - 1, Number(day))
  if (
    date.getFullYear() !== Number(year) ||
    date.getMonth() !== Number(month) - 1 ||
    date.getDate() !== Number(day)
  ) {
    return 'Meeting date must be a real date'
  }
  if (toIsoDate(parts) > toLocalIsoDate()) {
    return 'Meeting date must be today or in the past'
  }
  return true
}

export const toApiMeetingDate = (value?: string): string | null =>
  value && validateMeetingDate(value) === true
    ? toIsoDate(splitDate(value))
    : null

const DATE_FIELDS = [
  { part: 'day', label: 'Day', width: 2 },
  { part: 'month', label: 'Month', width: 2 },
  { part: 'year', label: 'Year', width: 4 },
] as const

export const MeetingDateField = () => {
  const { clearErrors } = useFormContext<TranscriptionForm>()
  const { field, fieldState } = useController<
    TranscriptionForm,
    'meeting_date'
  >({
    name: 'meeting_date',
    rules: { validate: validateMeetingDate },
  })
  const parts = splitDate(field.value)
  const error = fieldState.error?.message
  const hasDate = !!(parts.day || parts.month || parts.year)

  const setPart = (part: keyof DateParts, value: string) => {
    if (error) clearErrors('meeting_date')
    field.onChange(joinDate({ ...parts, [part]: value.replace(/\D/g, '') }))
  }

  return (
    <div
      className={`govuk-form-group ${error ? 'govuk-form-group--error' : ''}`}
    >
      <fieldset
        className="govuk-fieldset"
        role="group"
        aria-describedby={error ? 'meeting-date-error' : undefined}
      >
        <legend className="govuk-fieldset__legend">
          Meeting date (optional)
        </legend>
        {error && (
          <p id="meeting-date-error" className="govuk-error-message">
            <span className="govuk-visually-hidden">Error:</span> {error}
          </p>
        )}
        <div className="flex flex-wrap items-end">
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
                    value={parts[part]}
                    onChange={(e) => setPart(part, e.target.value)}
                    onBlur={field.onBlur}
                  />
                </div>
              </div>
            ))}
          </div>
          {hasDate && (
            <button
              type="button"
              className="govuk-link govuk-!-font-size-16 leading-10 text-(--govuk-link-colour) hover:cursor-pointer"
              onClick={() => {
                clearErrors('meeting_date')
                field.onChange('')
              }}
            >
              Provide no date
            </button>
          )}
        </div>
      </fieldset>
    </div>
  )
}
