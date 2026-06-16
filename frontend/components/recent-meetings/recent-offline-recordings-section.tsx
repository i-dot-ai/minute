'use client'

import {
  useOfflineRecordings,
} from '@/components/recent-meetings/use-offline-recordings'
import Link from 'next/link'

export function RecentOfflineRecordingsSection() {
  const { data: dbRecordings = [], isLoading } = useOfflineRecordings()

  if (isLoading || dbRecordings.length === 0) {
    return null
  }

  return (
    <div className="govuk-inset-text">
      You have <strong>{dbRecordings.length} incomplete recordings</strong> stored only in this browser.{' '}
      <Link className="govuk-notification-banner__link" href="/recordings">View incomplete recordings</Link> to upload them to the cloud or delete them.
    </div>
  )
}
