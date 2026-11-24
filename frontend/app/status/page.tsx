'use client'

import type { HourlyProcessingStatus } from '@/lib/processing-status'
import { useQuery } from '@tanstack/react-query'
import { Chart } from '@i-dot-ai-npm/component-library-react'

function formatProcessingTime(seconds: number | null): string {
  if (seconds == null) return 'N/A'
  const total = Math.round(seconds)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const remainingSeconds = total % 60
  if (hours) return `${hours}h ${minutes}m ${remainingSeconds}s`
  if (minutes) return `${minutes}m ${remainingSeconds}s`
  return `${remainingSeconds}s`
}

function Status(): React.JSX.Element {
  const { data, isPending, isError } = useQuery<HourlyProcessingStatus>({
    queryKey: ['processing-status-hourly'],
    queryFn: async () => {
      const response = await fetch('/api/status')
      if (!response.ok) throw new Error('Processing status unavailable')
      return response.json()
    },
    staleTime: 60_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: false,
    retry: false,
  })
  const recent = data?.last_10_minutes
  const failureRate = recent?.failure_rate
  const labels =
    data?.hours.map((hour) =>
      new Date(hour.start).toLocaleTimeString('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'Europe/London',
      })
    ) ?? []

  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds-from-desktop">
          <h1 className="govuk-heading-xl">System status</h1>
          <h2 className="govuk-heading-m">Minute is working normally</h2>
          <p className="govuk-body-s">Updated now</p>
        </div>
      </div>
      {isPending || isError || !recent ? (
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-two-thirds-from-desktop">
            <p className="govuk-body">
              {isPending
                ? 'Checking metrics…'
                : 'Metrics are temporarily unavailable.'}
            </p>
          </div>
        </div>
      ) : (
        <>
          {data.partial && (
            <div className="govuk-warning-text" role="status">
              <span className="govuk-warning-text__icon" aria-hidden="true">
                !
              </span>
              <strong className="govuk-warning-text__text">
                <span className="govuk-visually-hidden">Warning</span>
                Processing times are based on incomplete data because the
                reporting limit was reached. Transcription counts and error
                rates are not affected by this limit.
              </strong>
            </div>
          )}
          <div className="govuk-grid-row">
            <div className="govuk-grid-column-two-thirds-from-desktop">
              <h2 className="govuk-heading-l">Right now</h2>
              <p className="govuk-body">Last 10 mins</p>
            </div>
          </div>
          <div className="govuk-grid-row">
            <div className="govuk-grid-column-one-half govuk-grid-column-one-third-from-desktop">
              <div className="analytics-card analytics-card--blue">
                <h3 className="govuk-heading-s govuk-!-font-weight-regular">
                  Time to transcribe a 1-hour meeting
                </h3>
                <p className="govuk-body govuk-!-font-size-48 govuk-!-font-weight-bold">
                  {formatProcessingTime(recent.projected_one_hour_seconds)}
                </p>
                <p className="govuk-body">Usually about 1-3 mins</p>
              </div>
            </div>
            <div className="govuk-grid-column-one-half govuk-grid-column-one-third-from-desktop">
              <div className="analytics-card analytics-card--teal">
                <h3 className="govuk-heading-s govuk-!-font-weight-regular">
                  Transcriptions
                </h3>
                <p className="govuk-body govuk-!-font-size-48 govuk-!-font-weight-bold">
                  {recent.completed} completed
                </p>
                <p className="govuk-body">{recent.failed} failed</p>
              </div>
            </div>
          </div>
          <div className="govuk-grid-row govuk-!-margin-top-9">
            <div className="govuk-grid-column-two-thirds-from-desktop">
              <h2 className="govuk-heading-l">Last 24 hours</h2>
              <Chart
                title="Time to transcribe a 1 hour meeting"
                variant="line"
                showNullValuesAsZero
                format={(value) => formatProcessingTime(value as number)}
                data={{
                  heading: 'Time',
                  labels: labels,
                  datasets: [
                    {
                      label: 'Processing time',
                      data: data.hours.map((h) => h.projected_one_hour_seconds),
                    },
                  ],
                }}
              />
              <Chart
                title="Transcriptions completed per hour"
                variant="bar"
                data={{
                  heading: 'Count',
                  labels: labels,
                  datasets: [
                    {
                      label: 'Completed',
                      colour: 'teal-tint-25',
                      data: data.hours.map((h) => h.completed),
                    },
                  ],
                }}
              />
              <Chart
                title="Failed transcriptions per hour"
                variant="bar"
                data={{
                  heading: 'Error rate',
                  labels: labels,
                  datasets: [
                    {
                      label: 'Error rate',
                      colour: 'magenta',
                      data: data.hours.map((h) => h.failed),
                    },
                  ],
                }}
              />
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default Status
