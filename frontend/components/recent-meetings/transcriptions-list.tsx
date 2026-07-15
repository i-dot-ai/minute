'use client'

import {
  getTranscriptionDisplayTitle,
  RenameButton,
  RenameTitleInput,
  useRenameTranscription,
} from '@/components/recent-meetings/rename-transcription'
import { TranscriptionMetadata } from '@/lib/client'
import Link from 'next/link'
import { useCallback, useState } from 'react'

function TranscriptionTableRow({
  transcription,
  selectedIds,
  onToggle,
}: {
  transcription: TranscriptionMetadata
  selectedIds?: Set<string>
  onToggle?: (id: string, checked: boolean) => void
}) {
  const [editing, setEditing] = useState(false)
  const { save, isPending } = useRenameTranscription(transcription)
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

  const handleSubmit = useCallback(
    (title: string) => {
      save(title)
      setEditing(false)
    },
    [save]
  )

  return (
    <tr className="govuk-table__row relative hover:bg-[#f4f8fb]">
      <td>
        <div
          className="govuk-checkboxes govuk-checkboxes--small govuk-checkboxes--subtle flex"
          data-module="govuk-checkboxes"
        >
          <input
            className="govuk-checkboxes__input"
            id={`transcription-${transcription.id}`}
            name="transcription"
            type="checkbox"
            value={transcription.id}
            checked={selectedIds?.has(transcription.id) ?? false}
            onChange={(e) => onToggle?.(transcription.id, e.target.checked)}
          />
          <label
            className="govuk-label govuk-checkboxes__label"
            htmlFor={`transcription-${transcription.id}`}
          >
            <span className="govuk-visually-hidden">Select {displayTitle}</span>
          </label>
        </div>
      </td>
      <td className="flex-1">
        {editing ? (
          <RenameTitleInput
            transcription={transcription}
            isPending={isPending}
            onSubmit={handleSubmit}
            onCancel={() => setEditing(false)}
          />
        ) : (
          <Link
            href={`/transcriptions/${transcription.id}`}
            className="govuk-link govuk-link--no-visited-state govuk-link--no-underline relative flex flex-1 items-center gap-2 !text-(--govuk-text-colour)"
          >
            {displayTitle}
          </Link>
        )}
      </td>
      <td>
        <div className="govuk-button-group flex justify-end govuk-!-margin-right-2">
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
      </td>
      <td className="min-w-26">
        <span className="govuk-body-s govuk-!-margin-0">{date}</span>
      </td>
      <td className="text-center">
        <RenameButton
          displayTitle={displayTitle}
          disabled={editing || isPending}
          onClick={() => setEditing(true)}
        />
      </td>
    </tr>
  )
}

export function TranscriptionsList({
  transcriptions,
  selectedIds,
  onToggle,
}: {
  transcriptions: TranscriptionMetadata[]
  headingLevel?: 'h2' | 'h3'
  selectable?: boolean
  selectedIds?: Set<string>
  onToggle?: (id: string, checked: boolean) => void
}) {
  return (
    <table
      className="govuk-table govuk-table--subtle"
      aria-labelledby="transcriptions-list-heading"
    >
      <thead className="govuk-table__head">
        <tr className="govuk-table__row">
          <th scope="col" className="govuk-table__header">
            Select
          </th>
          <th scope="col" className="govuk-table__header">
            Title
          </th>
          <th scope="col" className="govuk-table__header !text-center">
            Status
          </th>
          <th scope="col" className="govuk-table__header">
            Date
          </th>
          <th scope="col" className="govuk-table__header">
            Rename
          </th>
        </tr>
      </thead>
      <tbody className="govuk-table__body">
        {transcriptions.map((transcription) => (
          <TranscriptionTableRow
            key={transcription.id}
            transcription={transcription}
            selectedIds={selectedIds}
            onToggle={onToggle}
          />
        ))}
      </tbody>
    </table>
  )
}
