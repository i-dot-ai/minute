'use client'

import type { ProcessingStatus } from '@/lib/processing-status'
import { useQuery } from '@tanstack/react-query'
import { CircleCheck } from 'lucide-react'
import { useSearchParams } from 'next/navigation'
import { useId, useState } from 'react'

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

export function ProcessingStatusPanel() {
  const [expanded, setExpanded] = useState(false)
  const metricsId = useId()
  const alert = useSearchParams().get('alert')
  const forcedFailureRate =
    alert === 'yellow' ? 0.0312 : alert === 'red' ? 0.2026 : undefined
  const { data, isPending, isError } = useQuery<ProcessingStatus>({
    queryKey: ['processing-status'],
    queryFn: async () => {
      const response = await fetch('/api/status')
      if (!response.ok) throw new Error('Processing status unavailable')
      return response.json()
    },
    staleTime: 60_000,
    refetchOnWindowFocus: false,
    retry: false,
    enabled: forcedFailureRate === undefined || expanded,
  })
  const transcription = data?.components.transcription
  const horizonSeconds = data?.horizon_seconds ?? 600
  const horizonUnit = horizonSeconds >= 86_400 ? 'day' : 'minute'
  const horizon = horizonSeconds / (horizonUnit === 'day' ? 86_400 : 60)
  const failureRate =
    forcedFailureRate ?? data?.components.transcription.failure_rate ?? 0
  const [colour, headline, message] =
    failureRate < 0.0001
      ? [
          'text-green-700',
          'We’re fully operational.',
          'We’re not aware of any issues affecting our systems.',
        ]
      : failureRate < 0.05
        ? [
            'text-yellow-600',
            'Degraded performance.',
            "We're aware of users experiencing errors.",
          ]
        : [
            'text-red-700',
            'Partial outage.',
            "We're aware of users experiencing elevated errors.",
          ]

  return (
    <section
      aria-label="Status"
      className="govuk-!-padding-4 govuk-!-margin-bottom-5 bg-(--govuk-surface-background-colour)"
      aria-live="polite"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        {forcedFailureRate === undefined && (isPending || isError || !data) ? (
          <p className="govuk-body-s govuk-!-margin-bottom-0">
            {isPending
              ? 'Checking status…'
              : 'Status is temporarily unavailable.'}
          </p>
        ) : (
          <p className="govuk-body-s govuk-!-margin-bottom-0 flex items-start gap-2">
            <CircleCheck
              aria-hidden="true"
              className={`mt-0.5 size-5 shrink-0 ${colour}`}
            />
            <span>
              <strong>{headline}</strong> {message}
            </span>
          </p>
        )}
        <button
          type="button"
          className="govuk-link govuk-!-font-size-16 shrink-0 cursor-pointer self-start whitespace-nowrap"
          aria-expanded={expanded}
          aria-controls={metricsId}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? 'Hide metrics' : 'Show metrics'}
        </button>
      </div>
      <div id={metricsId} hidden={!expanded} className="govuk-!-margin-top-4">
        <hr className="govuk-section-break govuk-section-break--visible govuk-!-margin-bottom-4" />
        {isPending || isError || !transcription ? (
          <p className="govuk-body-s govuk-!-margin-bottom-0">
            {isPending
              ? 'Checking metrics…'
              : 'Metrics are temporarily unavailable.'}
          </p>
        ) : (
          <>
            <p className="govuk-body-s govuk-!-margin-bottom-2">
              Last {horizon} {horizonUnit}
              {horizon === 1 ? '' : 's'}:
            </p>
            <ul className="govuk-list govuk-list--bullet govuk-!-font-size-16 govuk-!-margin-bottom-0">
              <li>Transcriptions: {transcription.counts.completed}</li>
              <li>
                Error rate:{' '}
                {(failureRate * 100).toLocaleString('en-GB', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
                %
              </li>
              {(['p50', 'p90', 'p99'] as const).map((percentile) => {
                const seconds =
                  transcription.processing_time_seconds[percentile]
                return (
                  <li key={percentile}>
                    Processing time ({percentile.toUpperCase()}):{' '}
                    {formatProcessingTime(seconds)}
                  </li>
                )
              })}
            </ul>
          </>
        )}
      </div>
    </section>
  )
}
