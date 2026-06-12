import { TranscriptionMetadata } from '@/lib/client'
import Link from 'next/link'

export function TranscriptionsList({
  transcriptions,
}: {
  transcriptions: TranscriptionMetadata[]
}) {
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
            <div>
              <h3 className="govuk-heading-s govuk-!-margin-bottom-1">
                <Link
                  href={`/transcriptions/${transcription.id}`}
                  className="govuk-link"
                >
                  {transcription.title ||
                    (['awaiting_start', 'in_progress'].includes(
                      transcription.status
                    )
                      ? 'Generating title'
                      : 'No title')}
                </Link>
              </h3>
              <p className="govuk-body-s govuk-!-margin-bottom-0">{date}</p>
            </div>
            {transcription.status === 'failed' && (
              <strong className="govuk-tag govuk-tag--red">Failed</strong>
            )}
            {transcription.status === 'awaiting_start' && (
              <strong className="govuk-tag govuk-tag--grey">
                Awaiting start
              </strong>
            )}
            {transcription.status === 'in_progress' && (
              <strong className="govuk-tag govuk-tag--grey">In progress</strong>
            )}
          </li>
        )
      })}
    </ul>
  )
}
