'use client'
import { PaginatedTranscriptions } from '@/components/recent-meetings/paginated-transcriptions'
import { getUserUsersMeGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { Suspense } from 'react'

export default function TranscriptionsPage() {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  console.log(user)

  return (
    <div className="govuk-!-padding-top-4">
      <div className="govuk-width-container">
        <div className="govuk-grid-row">
          <div
            className="govuk-grid-column-full"
            data-onboarding="saved-transcriptions-page"
          >
            <h1 className="govuk-heading-m" id="transcriptions-list-heading">
              Transcriptions
            </h1>
            {user && user.data_retention_days && (
              <p className="govuk-body">
                Your current data retention period is set to{' '}
                {user?.data_retention_days} day
                {user.data_retention_days > 1 ? 's' : ''}.{' '}
                <Link
                  href="/settings"
                  className="govuk-link govuk-link--no-visited-state"
                >
                  Change in settings
                </Link>
              </p>
            )}
          </div>
        </div>
        <Suspense fallback={<div>Loading...</div>}>
          <PaginatedTranscriptions />
        </Suspense>
      </div>
    </div>
  )
}
