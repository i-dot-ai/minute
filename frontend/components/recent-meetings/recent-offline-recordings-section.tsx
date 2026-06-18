'use client'

import { OfflineRecordingsList } from '@/components/recent-meetings/offline-recordings-list'
import {
  useOfflineRecordings,
} from '@/components/recent-meetings/use-offline-recordings'
import { Suspense } from 'react'

export function RecentOfflineRecordingsSection() {
  const { data: dbRecordings = [], isLoading } = useOfflineRecordings()

  if (isLoading || dbRecordings.length === 0) {
    return null
  }

  return (
    <>
      <div className="govuk-error-summary" data-module="govuk-error-summary">
        <div role="alert">
          <h2 className="govuk-error-summary__title">
            You have <strong>{dbRecordings.length} incomplete recordings</strong> stored only in this browser.{' '}
          </h2>
          <div className="govuk-error-summary__body">
            <p className="govuk-body">
              Please upload them to the cloud or delete them.
            </p>
            <Suspense fallback={<div>Loading...</div>}>
              <OfflineRecordingsList recordings={dbRecordings} />
            </Suspense>
          </div>
        </div>
      </div>
    </>
  )
}
