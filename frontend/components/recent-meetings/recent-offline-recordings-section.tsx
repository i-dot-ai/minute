'use client'

import { OfflineRecordingsList } from '@/components/recent-meetings/offline-recordings-list'
import {
  sortRecordingsNewestFirst,
  useOfflineRecordings,
} from '@/components/recent-meetings/use-offline-recordings'
import { Suspense, useMemo, useState } from 'react'

const INCOMPLETE_RECORDINGS_PREVIEW_LIMIT = 3

export function RecentOfflineRecordingsSection() {
  const { data: dbRecordings = [], isLoading } = useOfflineRecordings()
  const [showAll, setShowAll] = useState(false)

  const sortedRecordings = useMemo(
    () => sortRecordingsNewestFirst(dbRecordings),
    [dbRecordings]
  )

  const visibleRecordings = showAll
    ? sortedRecordings
    : sortedRecordings.slice(0, INCOMPLETE_RECORDINGS_PREVIEW_LIMIT)

  if (isLoading || dbRecordings.length === 0) {
    return null
  }

  return (
    <>
      <div className="govuk-error-summary" data-module="govuk-error-summary">
        <div role="alert">
          <h2 className="govuk-error-summary__title">
            You have{' '}
            <strong>{dbRecordings.length} incomplete recordings</strong> stored
            only in this browser.{' '}
          </h2>
          <div className="govuk-error-summary__body">
            <p className="govuk-body">
              Please upload them to the cloud or delete them.
            </p>
            <Suspense fallback={<div>Loading...</div>}>
              <OfflineRecordingsList recordings={visibleRecordings} />
            </Suspense>
            {sortedRecordings.length > INCOMPLETE_RECORDINGS_PREVIEW_LIMIT && (
              <button
                type="button"
                className="govuk-link govuk-!-margin-top-2"
                onClick={() => setShowAll((expanded) => !expanded)}
              >
                {showAll
                  ? 'Show fewer'
                  : `Show all (${sortedRecordings.length})`}
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
