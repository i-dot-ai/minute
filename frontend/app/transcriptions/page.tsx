'use client'

import { PaginatedTranscriptions } from '@/components/recent-meetings/paginated-transcriptions'
import { SettingsDialog } from '@/components/settings/settings-dialog'
import { getUserUsersMeGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { Suspense } from 'react'

export default function TranscriptionsPage() {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })

  return (
    <div className="govuk-!-padding-top-4">
      <div className="govuk-width-container">
        <div className="govuk-grid-row">
          <div
            className="govuk-grid-column-full"
            data-onboarding="saved-transcriptions-page"
          >
            <h1
              className="govuk-heading-l govuk-!-margin-bottom-3"
              id="transcriptions-list-heading"
            >
              Transcriptions
            </h1>
            {user && (
              <p className="govuk-body" id="tour-data-retention">
                Transcriptions will be{' '}
                {user.data_retention_days ? (
                  <>
                    deleted after {user.data_retention_days} day
                    {user.data_retention_days > 1 ? 's' : ''}
                  </>
                ) : (
                  <>kept indefinitely</>
                )}
                . <SettingsDialog user={user} />.
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
