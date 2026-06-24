import { DeleteTranscriptionButton } from '@/components/recent-meetings/delete-transcription-button'
import { RenameTranscriptionButton } from '@/components/recent-meetings/rename-transcription-button'
import { getTranscriptionDisplayTitle } from '@/components/recent-meetings/rename-transcription-dialog'
import { TranscriptionMetadata } from '@/lib/client'
import { getUserUsersMeGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { isExpiringTomorrow } from '@/utils/transcript-expiry'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'

export function TranscriptionsList({
  transcriptions,
}: {
  transcriptions: TranscriptionMetadata[]
}) {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  const isExpiringSoon = isExpiringTomorrow(
    transcriptions[0].created_datetime,
    user?.data_retention_days
  )
  return (
    <ul className="govuk-list">
      {transcriptions.map((transcription) => {
        const date = new Date(transcription.created_datetime).toLocaleString(
          'en-GB',
          {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          }
        )
        return (
          <li
            key={transcription.id}
            className="transcriptions__list-item govuk-!-padding-top-3 govuk-!-padding-bottom-3 flex items-center justify-between"
          >
            <div
              className={`${transcription.status === 'completed' ? 'flex-2' : 'flex-1'}`}
            >
              <h3 className="govuk-heading-s govuk-!-margin-bottom-1">
                <Link
                  href={`/transcriptions/${transcription.id}`}
                  className="govuk-link govuk-link--no-visited-state"
                >
                  {getTranscriptionDisplayTitle(
                    transcription.title,
                    transcription.status
                  )}
                </Link>
              </h3>
              <p className="govuk-body-s govuk-!-margin-bottom-0">{date}</p>
            </div>
            <div
              className={`govuk-button-group flex flex-1 justify-end ${isExpiringSoon ? 'flex-2' : ''}`}
            >
              {isExpiringSoon && (
                <strong className="govuk-tag govuk-tag--yellow govuk-!-margin-right-2">
                  Expiring soon
                </strong>
              )}
              {transcription.status === 'failed' && (
                <strong className="govuk-tag govuk-tag--red govuk-!-margin-right-2">
                  Failed
                </strong>
              )}
              {transcription.status === 'awaiting_start' && (
                <strong className="govuk-tag govuk-tag--grey govuk-!-margin-right-2">
                  Awaiting start
                </strong>
              )}
              {transcription.status === 'in_progress' && (
                <strong className="govuk-tag govuk-tag--grey govuk-!-margin-right-2">
                  In progress
                </strong>
              )}
              <RenameTranscriptionButton
                transcription={transcription}
                className="govuk-button govuk-button--secondary"
              />
              <DeleteTranscriptionButton transcription={transcription} />
            </div>
          </li>
        )
      })}
    </ul>
  )
}
