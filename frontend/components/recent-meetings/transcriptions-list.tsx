'use client'

import {
  getTranscriptionDisplayTitle,
  RenameTranscriptionInline,
} from '@/components/recent-meetings/rename-transcription'
import { DeleteTranscriptionButton } from '@/components/recent-meetings/delete-transcription-button'
import { TranscriptionMetadata } from '@/lib/client'
import Link from 'next/link'

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
        const displayTitle = getTranscriptionDisplayTitle(
          transcription.title,
          transcription.status
        )
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
                    Select {displayTitle}
                  </span>
                </label>
              </div>
            )}
            <div className="flex flex-1 items-center justify-between gap-2">
              <RenameTranscriptionInline
                transcription={transcription}
                headingLevel={ItemHeading}
                headingClassName="govuk-body govuk-!-margin-bottom-0"
              >
                {({ button, title, form, editing }) => (
                  <>
                    {!editing && (
                      <span className="relative z-10 shrink-0">{button}</span>
                    )}
                    {editing ? (
                      <div className="min-w-0 flex-1">{form}</div>
                    ) : (
                      <Link
                        href={`/transcriptions/${transcription.id}`}
                        className="govuk-link govuk-link--no-visited-state govuk-link--no-underline relative flex flex-1 items-center gap-2"
                      >
                        <ItemHeading className="flex-1">{title}</ItemHeading>
                        <div className="govuk-button-group govuk-!-margin-bottom-0 flex justify-end">
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
                        <p className="govuk-body-s govuk-!-margin-bottom-0 min-w-25 text-right">
                          {date}
                        </p>
                      </Link>
                    )}
                  </>
                )}
              </RenameTranscriptionInline>
              <span className="relative z-10 shrink-0">
                <DeleteTranscriptionButton
                  transcription={transcription}
                  title={displayTitle}
                />
              </span>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
