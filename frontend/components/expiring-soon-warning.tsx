'use client'

import { useTranscriptions } from '@/components/recent-meetings/use-transcriptions'
import { getUserUsersMeGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { isExpiringTomorrow } from '@/utils/transcript-expiry'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'

const ExpiringSoonWarning = () => {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  const { data: firstPage } = useTranscriptions({ page: 1, pageSize: 1 })
  const lastPage = firstPage?.total_pages ?? 1
  const { data: oldest } = useTranscriptions({
    page: lastPage,
    pageSize: 1,
  })
  const transcriptions = oldest?.items ?? []

  if (!transcriptions.length) return null
  const oldestTranscription = transcriptions[0]
  const isExpiringSoon = isExpiringTomorrow(
    oldestTranscription.created_datetime,
    user?.data_retention_days
  )

  if (!isExpiringSoon) return null

  return (
    <div className="govuk-warning-text">
      <span className="govuk-warning-text__icon" aria-hidden="true">
        !
      </span>
      <strong className="govuk-warning-text__text">
        <span className="govuk-visually-hidden">Warning</span>
        You have transcriptions that will expire in 1 day.{' '}
        <Link
          href={`/transcriptions?page=${lastPage}`}
          className="govuk-link govuk-link--no-visited-state"
        >
          View the oldest transcriptions
        </Link>
      </strong>
    </div>
  )
}

export default ExpiringSoonWarning
