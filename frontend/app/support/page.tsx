'use client'

import {
  createSupportTicketSupportTicketsPostMutation,
  getUserUsersMeGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { CreateSupportTicketRequest } from '@/lib/client/types.gen'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'

const CATEGORIES = [
  { value: 'issue', label: 'I am facing an issue with Minute' },
  { value: 'access', label: 'I need access for a colleague' },
  { value: 'recommendation', label: 'I have a recommendation' },
  { value: 'general', label: 'General enquiry/Other' },
] as const

const SUPPORT_EMAIL = 'minute-support@dsit.gov.uk'

function EmailLink() {
  return (
    <a href={`mailto:${SUPPORT_EMAIL}`} className="govuk-link">
      {SUPPORT_EMAIL}
    </a>
  )
}

function SupportForm() {
  const form = useForm<CreateSupportTicketRequest>({
    defaultValues: { category: 'issue' },
  })
  const { errors } = form.formState
  const {
    mutate: createTicket,
    data: ticket,
    isPending,
    isError,
  } = useMutation({ ...createSupportTicketSupportTicketsPostMutation() })

  if (ticket) {
    return (
      <div className="govuk-panel govuk-panel--confirmation">
        <h2 className="govuk-panel__title">Message sent</h2>
        <div className="govuk-panel__body">
          Your reference is
          <br />
          <strong>{ticket.reference}</strong>
        </div>
      </div>
    )
  }

  const fieldErrors = [
    { id: 'message', message: errors.message?.message },
  ].filter((e) => e.message)

  return (
    <form
      noValidate
      className="govuk-!-padding-5 bg-(--govuk-surface-background-colour)"
      onSubmit={form.handleSubmit((body) => createTicket({ body }))}
    >
      {(fieldErrors.length > 0 || isError) && (
        <div className="govuk-error-summary" role="alert" tabIndex={-1}>
          <h2 className="govuk-error-summary__title">There is a problem</h2>
          <div className="govuk-error-summary__body">
            {isError && (
              <p className="govuk-body">
                Your message could not be sent. Please try again or email us at{' '}
                <EmailLink />.
              </p>
            )}
            {fieldErrors.length > 0 && (
              <ul className="govuk-list govuk-error-summary__list">
                {fieldErrors.map((e) => (
                  <li key={e.id}>
                    <a href={`#${e.id}`}>{e.message}</a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      <div className="govuk-form-group">
        <label className="govuk-label govuk-label--s" htmlFor="category">
          What is your message about?
        </label>
        <select
          className="govuk-select"
          id="category"
          aria-describedby="category-hint"
          {...form.register('category')}
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <div
        className={`govuk-form-group ${errors.message ? 'govuk-form-group--error' : ''}`}
      >
        <label className="govuk-label govuk-label--s" htmlFor="message">
          Message
        </label>
        {errors.message && (
          <p className="govuk-error-message">
            <span className="govuk-visually-hidden">Error:</span>{' '}
            {errors.message.message}
          </p>
        )}
        <textarea
          className={`govuk-textarea bg-white ${errors.message ? 'govuk-textarea--error' : ''}`}
          id="message"
          rows={6}
          {...form.register('message', {
            required: 'Enter a message',
            maxLength: {
              value: 5000,
              message: 'Message must be 5000 characters or fewer',
            },
          })}
        />
      </div>

      <button type="submit" className="govuk-button" disabled={isPending}>
        Send message
      </button>
    </form>
  )
}

export default function SupportPage() {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })

  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl">Contact us</h1>
          {user && (
            <>
              <h2 className="govuk-heading-l">Raise a ticket</h2>
              <p className="govuk-body">
                The best way to contact us is to raise a support ticket using
                the form below.
              </p>
              <div className="govuk-inset-text">
                We will add your User ID to the ticket so we can identify your
                account.
              </div>
              <SupportForm />
            </>
          )}
          <h2 className="govuk-heading-l govuk-!-margin-top-6">Email</h2>
          <p className="govuk-body">
            You can email us at:
            <EmailLink />
          </p>
          <p className="govuk-body">
            We aim to respond to all inquiries within 24 hours.
          </p>
        </div>
      </div>
    </div>
  )
}
