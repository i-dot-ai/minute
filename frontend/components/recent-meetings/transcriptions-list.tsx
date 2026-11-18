'use client'

import { DeleteTranscriptionButton } from '@/components/recent-meetings/delete-transcription-button'
import {
  getTranscriptionDisplayTitle,
  isTranscriptionProcessing,
  RenameButton,
  RenameTitleInput,
  useRenameTranscription,
} from '@/components/recent-meetings/rename-transcription'
import { IncompleteRecordingTableRow } from '@/components/recent-meetings/incomplete-recording-table-row'
import { TranscriptionMetadata, TranscriptionSearchResult } from '@/lib/client'
import { RecordingDbItem } from '@/providers/transcription-db-provider'
import Link from 'next/link'
import { useCallback, useState } from 'react'
import { MatchSnippet } from '@/app/search/search-results'
import { searchResultHref } from '@/lib/search-match'
import { formatTime } from '@/components/audio/audio-player'

function TranscriptionTableRow({
  transcription,
  selectedIds,
  onToggle,
}: {
  transcription: TranscriptionMetadata &
    Partial<Pick<TranscriptionSearchResult, 'matches' | 'matches_truncated'>>
  selectedIds?: Set<string>
  onToggle?: (id: string, checked: boolean) => void
}) {
  const [editing, setEditing] = useState(false)
  const { save, isPending } = useRenameTranscription(transcription)
  const displayTitle = getTranscriptionDisplayTitle(
    transcription.title,
    transcription.status
  )
  const created = new Date(transcription.created_datetime)
  const isEarlierYear = created.getFullYear() < new Date().getFullYear()
  const date = created.toLocaleString('en-GB', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    year: isEarlierYear ? '2-digit' : undefined,
  })
  const searchMatch = transcription.matches?.filter(
    ({ source }) => source !== 'title'
  )
  const titleMatch = transcription.matches?.find(
    ({ source }) => source === 'title'
  )

  const handleSubmit = useCallback(
    (title: string) => {
      save(title)
      setEditing(false)
    },
    [save]
  )

  return (
    <tr className="govuk-table__row hover:bg-[#f4f8fb] has-[:checked]:bg-[#f4f8fb]">
      <td className="govuk-table__cell govuk-!-padding-top-1 govuk-!-padding-bottom-1 hidden sm:table-cell">
        <div className="govuk-!-padding-left-1 flex items-center gap-2">
          <div
            className="govuk-checkboxes govuk-checkboxes--small govuk-checkboxes--subtle relative flex"
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
              className="govuk-label govuk-checkboxes__label govuk-!-padding-0"
              htmlFor={`transcription-${transcription.id}`}
            >
              <span className="govuk-visually-hidden">
                Select {displayTitle}
              </span>
            </label>
          </div>
        </div>
      </td>
      <td className="govuk-table__cell govuk-!-padding-right-1 govuk-!-padding-top-3 govuk-!-padding-bottom-3 w-full">
        {editing ? (
          <RenameTitleInput
            transcription={transcription}
            isPending={isPending}
            onSubmit={handleSubmit}
            onCancel={() => setEditing(false)}
          />
        ) : (
          <>
            <Link
              href={`/transcriptions/${transcription.id}`}
              className="govuk-link govuk-link--no-visited-state govuk-link--no-underline relative my-2 flex-1 !text-(--govuk-link-colour)"
            >
              {titleMatch ? (
                <MatchSnippet
                  match={{
                    ...titleMatch,
                    snippet: displayTitle,
                    snippet_start: 0,
                    highlights: titleMatch.highlights.map(({ start, end }) => ({
                      start: start + titleMatch.snippet_start,
                      end: end + titleMatch.snippet_start,
                    })),
                  }}
                />
              ) : (
                displayTitle
              )}
              <div className="govuk-!-margin-top-2 govuk-!-margin-bottom-2 lg:hidden">
                <StatusTagList transcription={transcription} />
              </div>
            </Link>
            <p className="govuk-body-s govuk-!-margin-bottom-2 govuk-!-margin-top-1 md:hidden">
              {date}
            </p>
            {searchMatch?.length ? (
              <p className="govuk-body-s govuk-!-margin-bottom-0 govuk-!-margin-top-1">
                <MatchSnippet match={searchMatch[0]} />
                ...
              </p>
            ) : (
              <></>
            )}
          </>
        )}
      </td>
      <td className="govuk-table__cell govuk-!-padding-top-3 govuk-!-padding-bottom-3 hidden whitespace-nowrap md:table-cell">
        <span className="govuk-body-s govuk-!-margin-0">{date}</span>
      </td>
      <td className="govuk-table__cell govuk-!-padding-left-4 govuk-!-padding-right-4 govuk-!-padding-top-3 govuk-!-padding-bottom-3 hidden whitespace-nowrap lg:table-cell">
        <StatusTagList transcription={transcription} />
      </td>
      <td className="govuk-table__cell govuk-!-padding-right-1 govuk-!-padding-top-3 govuk-!-padding-bottom-3 whitespace-nowrap">
        <div className="flex items-center justify-end gap-2">
          {!isTranscriptionProcessing(transcription.status) && (
            <RenameButton
              displayTitle={displayTitle}
              disabled={editing || isPending}
              onClick={() => setEditing(true)}
            />
          )}
          <DeleteTranscriptionButton
            transcription={transcription}
            noUnderline={true}
            title={displayTitle}
            disabled={editing || isPending}
          />
        </div>
      </td>
    </tr>
  )
}

export function TranscriptionsList({
  transcriptions,
  offlineRecordings = [],
  selectedIds,
  onToggle,
}: {
  transcriptions: TranscriptionMetadata[]
  offlineRecordings?: RecordingDbItem[]
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
      <thead className="govuk-table__head sticky top-0 z-10 bg-white">
        <tr className="govuk-table__row">
          <th scope="col" className="govuk-table__header hidden sm:table-cell">
            Select
          </th>
          <th scope="col" className="govuk-table__header">
            <span className="hidden sm:inline">
              Transcription
              {offlineRecordings.length > 0 && <> and audio</>}
            </span>
            <span className="sm:hidden">Transcription</span>
          </th>
          <th scope="col" className="govuk-table__header hidden md:table-cell">
            Date
          </th>
          <th scope="col" className="govuk-table__header hidden lg:table-cell">
            Status
          </th>
          <th scope="col" className="govuk-table__header">
            Actions
          </th>
        </tr>
      </thead>
      <tbody className="govuk-table__body">
        {offlineRecordings.map((recording) => (
          <IncompleteRecordingTableRow
            key={recording.recording_id}
            recording={recording}
            selectedIds={selectedIds}
            onToggle={onToggle}
          />
        ))}
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

const StatusTagList = ({
  transcription,
}: {
  transcription: TranscriptionMetadata
}) => {
  return (
    <>
      {transcription.expiring && (
        <strong className="govuk-tag govuk-tag--yellow govuk-!-margin-right-1 govuk-!-padding-left-1 govuk-!-font-size-16">
          Expiring soon
        </strong>
      )}
      {transcription.status === 'failed' && (
        <strong className="govuk-tag govuk-tag--red govuk-!-margin-right-1 govuk-!-padding-left-1 govuk-!-font-size-16">
          Failed
        </strong>
      )}
      {transcription.no_speech_detected && (
        <strong className="govuk-tag govuk-tag--grey govuk-!-margin-right-1 govuk-!-padding-left-1 govuk-!-font-size-16">
          No audio
        </strong>
      )}
      {transcription.status === 'awaiting_start' && (
        <strong className="govuk-tag govuk-tag--grey govuk-!-margin-right-1 govuk-!-padding-left-1 govuk-!-font-size-16">
          Awaiting start
        </strong>
      )}
      {transcription.status === 'in_progress' && (
        <strong className="govuk-tag govuk-tag--grey govuk-!-margin-right-1 govuk-!-padding-left-1 govuk-!-font-size-16">
          In progress
        </strong>
      )}
    </>
  )
}
