'use client'

import { OfflineRecordingsList } from '@/components/recent-meetings/offline-recordings-list'
import {
  sortRecordingsNewestFirst,
  useOfflineRecordings,
} from '@/components/recent-meetings/use-offline-recordings'

export const OfflineRecordings = () => {
  const { data: dbRecordings = [], isLoading } = useOfflineRecordings()

  if (isLoading) {
    return <p className="govuk-body">Loading incomplete recordings...</p>
  }

  if (dbRecordings.length === 0) {
    return (
      <p className="govuk-body">
        No incomplete recordings found. Any recordings that have been made are
        either deleted or have been uploaded to the cloud.
      </p>
    )
  }

  const recordings = sortRecordingsNewestFirst(dbRecordings)

  return (
    <>
      <OfflineRecordingsList recordings={recordings} />
    </>
  )
}
