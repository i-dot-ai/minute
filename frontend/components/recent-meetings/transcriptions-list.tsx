import { getTranscriptionDisplayTitle } from '@/components/recent-meetings/rename-transcription-dialog'
import { TranscriptionMetadata } from '@/lib/client'
import { DeleteTranscriptionButton } from '@/components/recent-meetings/delete-transcription-button'
import Link from 'next/link'
import { RenameTranscriptionButton } from '@/components/recent-meetings/rename-transcription-button'

export function TranscriptionsList({
  transcriptions,
  headingLevel = 'h2',
  selectable = false,
  selectedIds,
  onToggle,
}: {
  transcriptions: TranscriptionMetadata[]
  headingLevel?: 'h2' | 'h3'
  selectable?: boolean
  selectedIds?: Set<string>
  onToggle?: (id: string, checked: boolean) => void
}) {
  const ItemHeading = headingLevel
  return (
    <ul className="govuk-list">
      {transcriptions.map((transcription) => {
        const date = new Date(transcription.created_datetime).toLocaleString(
          'en-GB',
          {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          }
        )
        return (
          <li
            key={transcription.id}
            className="transcriptions__list-item govuk-!-margin-bottom-0 flex items-center justify-between relative hover:bg-[#f4f8fb]"
          >
            {selectable && (
              <div
                className="govuk-checkboxes govuk-checkboxes--small flex"
                data-module="govuk-checkboxes"
              >
                <input
                  className="govuk-checkboxes__input"
                  id={`transcription-${transcription.id}`}
                  name="transcription"
                  type="checkbox"
                  value={transcription.id}
                  checked={selectedIds?.has(transcription.id) ?? false}
                  onChange={(e) =>
                    onToggle?.(transcription.id, e.target.checked)
                  }
                />
                <label
                  className="govuk-label govuk-checkboxes__label"
                  htmlFor={`transcription-${transcription.id}`}
                >
                  <span className="govuk-visually-hidden">
                    Select{' '}
                    {getTranscriptionDisplayTitle(
                      transcription.title,
                      transcription.status
                    )}
                  </span>
                </label>
              </div>
            )}
            <div className="flex flex-1 items-center justify-between gap-2">
              <RenameTranscriptionButton transcription={transcription} title={getTranscriptionDisplayTitle(transcription.title, transcription.status)} />
              <Link
                href={`/transcriptions/${transcription.id}`}
                className="govuk-link govuk-link--no-visited-state govuk-link--no-underline flex-1 flex"
              >
                <ItemHeading className="govuk-body govuk-!-margin-bottom-0 flex-1">
                  {getTranscriptionDisplayTitle(
                    transcription.title,
                    transcription.status
                  )}
                </ItemHeading>
                <div className="govuk-button-group govuk-!-margin-bottom-0 govuk-!-margin-right-2 flex justify-end">
                  {transcription.expiring && (
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
                </div>
                <p className="govuk-body-s govuk-!-margin-bottom-0">{date}</p>
              </Link>
              <DeleteTranscriptionButton transcription={transcription} title={getTranscriptionDisplayTitle(transcription.title, transcription.status)} />
            </div>
          </li>
        )
      })}
    </ul>
  )
}
