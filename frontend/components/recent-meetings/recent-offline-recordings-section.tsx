'use client'

import { DiscardConfirmDialog } from '@/components/audio/discard-dialog'
import { OfflineRecordingRow } from '@/components/recent-meetings/offline-recording-row'
import {
  sortRecordingsNewestFirst,
  useOfflineRecordings,
} from '@/components/recent-meetings/use-offline-recordings'
import { useRecordingDb } from '@/providers/transcription-db-provider'
import { useQueryClient } from '@tanstack/react-query'
import posthog from 'posthog-js'
import { Suspense, useEffect, useMemo, useRef, useState } from 'react'

const INCOMPLETE_RECORDINGS_PREVIEW_LIMIT = 3

export function RecentOfflineRecordingsSection() {
  const { data: dbRecordings = [], isLoading } = useOfflineRecordings()
  const { removeRecording } = useRecordingDb()
  const queryClient = useQueryClient()
  const [showAll, setShowAll] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const selectAllRef = useRef<HTMLInputElement>(null)

  const sortedRecordings = useMemo(
    () => sortRecordingsNewestFirst(dbRecordings),
    [dbRecordings]
  )

  const visibleRecordings = showAll
    ? sortedRecordings
    : sortedRecordings.slice(0, INCOMPLETE_RECORDINGS_PREVIEW_LIMIT)

  const visibleIds = visibleRecordings.map((r) => r.recording_id)
  const allVisibleSelected =
    visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id))
  const someVisibleSelected = visibleIds.some((id) => selectedIds.has(id))
  const selectedCount = selectedIds.size

  useEffect(() => {
    setSelectedIds(new Set())
  }, [showAll])

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate =
        someVisibleSelected && !allVisibleSelected
    }
  }, [someVisibleSelected, allVisibleSelected])

  const toggleOne = (id: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (checked) {
        next.add(id)
      } else {
        next.delete(id)
      }
      return next
    })
  }

  const toggleAll = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (allVisibleSelected) {
        visibleIds.forEach((id) => next.delete(id))
      } else {
        visibleIds.forEach((id) => next.add(id))
      }
      return next
    })
  }

  const handleBulkDelete = () => {
    selectedIds.forEach((id) => {
      const recording = dbRecordings.find((r) => r.recording_id === id)
      removeRecording(id)
      posthog.capture('offline_recording_deleted', {
        size: recording?.blob.size,
      })
    })
    queryClient.invalidateQueries({ queryKey: ['list-db-recordings'] })
    setSelectedIds(new Set())
  }

  if (isLoading || dbRecordings.length === 0) {
    return null
  }

  return (
    <div className="govuk-error-summary" data-module="govuk-error-summary">
      <div role="alert">
        <h2
          className="govuk-error-summary__title"
          id="recent-offline-recordings-section-title"
        >
          You have <strong>{dbRecordings.length} incomplete recordings</strong>{' '}
          stored only in this browser.{' '}
        </h2>
        <div className="govuk-error-summary__body">
          <p className="govuk-body">
            Please upload them to the cloud or delete them.
          </p>
          <div className="govuk-!-margin-bottom-3 govuk-!-padding-bottom-2 flex items-center gap-2 border-b border-(--govuk-border-colour)">
            <div
              className="govuk-checkboxes govuk-checkboxes--small relative flex"
              data-module="govuk-checkboxes"
            >
              <input
                ref={selectAllRef}
                className="govuk-checkboxes__input"
                id="select-all-offline"
                name="select-all-offline"
                type="checkbox"
                checked={allVisibleSelected}
                onChange={toggleAll}
                disabled={visibleRecordings.length === 0}
              />
              <label
                className="govuk-label govuk-checkboxes__label ml-3 whitespace-nowrap"
                htmlFor="select-all-offline"
              >
                Select all
              </label>
            </div>
            {selectedCount > 0 && (
              <div className="govuk-button-group govuk-!-margin-bottom-0">
                <button
                  type="button"
                  className="govuk-link link--warning govuk-!-margin-0"
                  onClick={() => setDeleteDialogOpen(true)}
                >
                  Delete {selectedCount} selected
                </button>
              </div>
            )}
            <span className="govuk-visually-hidden" aria-live="polite">
              {selectedCount > 0 ? `${selectedCount} recordings selected` : ''}
            </span>
          </div>
          <Suspense fallback={<div>Loading...</div>}>
            <table
              className="govuk-table"
              aria-labelledby="recent-offline-recordings-section-title"
            >
              <thead className="govuk-table__head govuk-visually-hidden">
                <tr className="govuk-table__row">
                  <th scope="col" className="govuk-table__header">
                    Select
                  </th>
                  <th scope="col" className="govuk-table__header">
                    Recording
                  </th>
                  <th scope="col" className="govuk-table__header">
                    Date
                  </th>
                  <th scope="col" className="govuk-table__header">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="govuk-table__body">
                {visibleRecordings.map((recording) => (
                  <OfflineRecordingRow
                    recording={recording}
                    selectedIds={selectedIds}
                    onToggle={toggleOne}
                    key={recording.recording_id}
                  />
                ))}
              </tbody>
            </table>
          </Suspense>
          {sortedRecordings.length > INCOMPLETE_RECORDINGS_PREVIEW_LIMIT && (
            <button
              type="button"
              className="govuk-link govuk-!-margin-top-2"
              onClick={() => setShowAll((expanded) => !expanded)}
            >
              {showAll ? 'Show fewer' : `Show all (${sortedRecordings.length})`}
            </button>
          )}
        </div>
      </div>
      <DiscardConfirmDialog
        open={deleteDialogOpen}
        setOpen={setDeleteDialogOpen}
        title={`Are you sure you want to discard ${selectedCount} recording${
          selectedCount === 1 ? '' : 's'
        }?`}
        description={`${
          selectedCount === 1 ? 'This recording has' : 'These recordings have'
        } not been uploaded yet. Discarding ${
          selectedCount === 1 ? 'it' : 'them'
        } will delete ${selectedCount === 1 ? 'it' : 'them'} permanently.`}
        confirmLabel={`Discard ${selectedCount} recording${
          selectedCount === 1 ? '' : 's'
        }`}
        onClickConfirm={() => {
          handleBulkDelete()
          setDeleteDialogOpen(false)
        }}
      />
    </div>
  )
}
