'use client'

import type { HourlyProcessingStatus } from '@/lib/processing-status'
import { useQuery } from '@tanstack/react-query'
import { LineChart } from '@/components/ui/line-chart'

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
      const response = await fetch(`/api/status${window.location.search}`)
      if (!response.ok) throw new Error('Processing status unavailable')
      return response.json()
    },
    staleTime: 60_000,
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
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl">Status</h1>
        </div>
      </div>
      {isPending || isError || !recent ? (
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-two-thirds">
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
            <div className="govuk-grid-column-two-thirds">
              <h2 className="govuk-heading-l">Last 10 mins</h2>
            </div>
          </div>
          <div className="govuk-grid-row">
            <div className="govuk-grid-column-one-third-from-desktop">
              <div className="analytics-card analytics-card--blue">
                <h3 className="govuk-heading-m govuk-!-font-weight-regular">
                  Processing time per audio hour:
                </h3>
                <p className="govuk-body govuk-!-font-size-48 govuk-!-font-weight-bold">
                  {formatProcessingTime(recent.per_audio_hour_seconds.p50)}
                </p>
              </div>
            </div>
            <div className="govuk-grid-column-one-third-from-desktop">
              <div className="analytics-card analytics-card--red">
                <h3 className="govuk-heading-m govuk-!-font-weight-regular">
                  Error rate:
                </h3>
                <p className="govuk-body govuk-!-font-size-48 govuk-!-font-weight-bold">
                  {failureRate == null
                    ? 'N/A'
                    : `${(failureRate * 100).toLocaleString('en-GB', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}%`}
                </p>
              </div>
            </div>
            <div className="govuk-grid-column-one-third-from-desktop">
              <div className="analytics-card analytics-card--teal">
                <h3 className="govuk-heading-m govuk-!-font-weight-regular">
                  Transcriptions completed:
                </h3>
                <p className="govuk-body govuk-!-font-size-48 govuk-!-font-weight-bold">
                  {recent.completed}
                </p>
              </div>
            </div>
          </div>
          <div className="govuk-grid-row govuk-!-margin-top-9">
            <div className="govuk-grid-column-two-thirds">
              <h2 className="govuk-heading-l">Last 24 hours</h2>
            </div>
          </div>
          <div className="govuk-grid-row">
            <div className="govuk-grid-column-full govuk-grid-column-one-half-from-desktop">
              <LineChart
                title="Processing time per audio hour"
                format={formatProcessingTime}
                labels={labels}
                series={[
                  {
                    label: 'Median',
                    colour: '#0F385C',
                    data: data.hours.map((h) => h.per_audio_hour_seconds.p50),
                  },
                  {
                    label: 'Slowest 10%',
                    colour: '#5694CA',
                    dash: [6, 4],
                    data: data.hours.map((h) => h.per_audio_hour_seconds.p90),
                  },
                  {
                    label: 'Slowest 1%',
                    colour: '#8EB8DC',
                    dash: [2, 3],
                    data: data.hours.map((h) => h.per_audio_hour_seconds.p99),
                  },
                ]}
              />
              <LineChart
                title="Transcriptions completed per hour"
                integer
                labels={labels}
                series={[
                  {
                    label: 'Completed',
                    colour: '#50A1A5',
                    data: data.hours.map((h) => h.completed),
                  },
                ]}
              />
            </div>
            <div className="govuk-grid-column-full govuk-grid-column-one-half-from-desktop">
              <LineChart
                title="Error rate per hour"
                format={(value) =>
                  `${value.toLocaleString('en-GB', { maximumFractionDigits: 2 })}%`
                }
                labels={labels}
                series={[
                  {
                    label: 'Error rate',
                    colour: '#CA357C',
                    data: data.hours.map((h) =>
                      h.failure_rate == null ? null : h.failure_rate * 100
                    ),
                  },
                ]}
              />
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default Status
