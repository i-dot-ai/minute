'use client'

import { useTranscriptions } from '@/components/recent-meetings/use-transcriptions'
import Link from 'next/link'

const ExpiringSoonWarning = () => {
  const { data: expiringTranscriptions } = useTranscriptions({
    page: 1,
    pageSize: 1,
    filterBy: 'expiring-soon',
  })

  if (!expiringTranscriptions?.total_count) return null

  return (
    <div className="govuk-warning-text">
      <span className="govuk-warning-text__icon" aria-hidden="true">
        !
      </span>
      <strong className="govuk-warning-text__text">
        <span className="govuk-visually-hidden">Warning</span>
        You have {expiringTranscriptions.total_count} transcription
        {expiringTranscriptions.total_count > 1 ? 's' : ''} that will be deleted
        tonight.{' '}
        <Link
          href={`/transcriptions?expiring=true`}
          className="govuk-link govuk-link--no-visited-state"
        >
          View your expiring transcriptions
        </Link>
      </strong>
    </div>
  )
}

export default ExpiringSoonWarning
