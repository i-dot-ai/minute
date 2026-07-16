'use client'

import { AiEditPopover } from '@/app/transcriptions/[transcriptionId]/MinuteTab/minute-editor/ai-edit-popover'
import {
  MinuteEditState,
  MinuteEditor,
  MinuteExportState,
} from '@/app/transcriptions/[transcriptionId]/MinuteTab/minute-editor/minute-editor'
import { ExportSummaryDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/ExportSummaryDialog'
import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
import { TranscriptionSidePanel } from '@/app/transcriptions/[transcriptionId]/MinuteTab/components/TranscriptionSidePanel'
import { DeleteTranscriptionButton } from '@/components/recent-meetings/delete-transcription-button'
import { useRenameTranscription } from '@/components/recent-meetings/rename-transcription'
import {
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { Eye, EyeOffIcon, Loader2, PencilIcon, Save } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'

export default function SummaryPage({
  params: { transcriptionId, minuteId },
}: {
  params: { transcriptionId: string; minuteId: string }
}) {
  const router = useRouter()
  const { data: transcription, isLoading } = useQuery({
    ...getTranscriptionTranscriptionsTranscriptionIdGetOptions({
      path: { transcription_id: transcriptionId },
    }),
  })

  const { data: minutes = [] } = useQuery({
    ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions(
      {
        path: { transcription_id: transcriptionId },
      }
    ),
  })

  const [exportState, setExportState] = useState<MinuteExportState | null>(null)
  const [editState, setEditState] = useState<MinuteEditState | null>(null)
  const [draftTitle, setDraftTitle] = useState('')

  const { save: saveTitle } = useRenameTranscription({
    id: transcriptionId,
    title: transcription?.title,
    status: transcription?.status ?? 'completed',
  })

  useEffect(() => {
    if (editState?.isEditable && transcription) {
      setDraftTitle(transcription.title ?? '')
    }
  }, [editState?.isEditable, transcription])

  const handleSave = useCallback(() => {
    saveTitle(draftTitle)
    editState?.onSave()
  }, [draftTitle, editState, saveTitle])

  const handleDiscard = useCallback(() => {
    setDraftTitle(transcription?.title ?? '')
    editState?.onCancel()
  }, [editState, transcription?.title])

  if (isLoading) {
    return (
      <div className="flex items-center gap-2">
        <Loader2 className="animate-spin" />
        <p className="govuk-body govuk-!-margin-bottom-0">Loading...</p>
      </div>
    )
  }

  if (!transcription) {
    return (
      <>
        <h1 className="govuk-heading-l govuk-!-margin-bottom-2">
          404 - Transcription not found
        </h1>
        <p className="govuk-body">
          The transcription you are looking for does not exist.
        </p>
        <div className="govuk-button-group">
          <Link href="/transcriptions" className="govuk-button">
            Back to transcriptions
          </Link>
        </div>
      </>
    )
  }

  const minute = minutes.find((m) => m.id === minuteId)

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
    <div className="govuk-grid-row">
      <div className="govuk-grid-column-one-quarter">
        <TranscriptionSidePanel
          transcriptionId={transcriptionId}
          minutes={minutes}
        />
      </div>
      <div className="govuk-grid-column-three-quarters">
        <div className="govuk-!-margin-bottom-6 border-b border-(--govuk-border-colour)">
          <div className="flex justify-between">
            <div className="govuk-button-group govuk-!-margin-bottom-0">
              <NewMinuteDialog
                transcriptionId={transcriptionId}
                disabled={editState?.isEditable}
                onCreated={() =>
                  router.push(`/transcriptions/${transcriptionId}/summary`)
                }
              />
            </div>
            <div className="govuk-button-group govuk-!-margin-bottom-0 justify-end">
              {editState && (
                <>
                  <button
                    className="govuk-button govuk-button--secondary"
                    onClick={() => editState.setIsEditable(true)}
                    type="button"
                    disabled={editState.isEditable}
                  >
                    <PencilIcon className="size-4" /> Edit
                  </button>
                  <ExportSummaryDialog
                    exportState={exportState}
                    title={transcription.title}
                    dialogueEntries={transcription.dialogue_entries}
                    disabled={editState.isEditable}
                  />
                  {editState.hasCitations && (
                    <button
                      className="govuk-button govuk-button--secondary min-w-48"
                      onClick={editState.toggleHideCitations}
                      disabled={editState.isEditable}
                    >
                      {editState.hideCitations ? (
                        <Eye className="size-4" />
                      ) : (
                        <EyeOffIcon className="size-4" />
                      )}
                      {editState.hideCitations
                        ? 'Show references'
                        : 'Hide references'}
                    </button>
                  )}

                  <DeleteTranscriptionButton
                    transcription={transcription}
                    disabled={editState?.isEditable}
                  />
                </>
              )}
            </div>
          </div>
          {editState && editState.isEditable && (
            <div className="flex flex-col justify-between lg:flex-row">
              <div className="govuk-form-group govuk-!-margin-bottom-3">
                <label className="govuk-label" htmlFor="version">
                  Version history
                </label>
                <select
                  className="govuk-select w-full"
                  id="version"
                  name="version"
                  onChange={(e) => editState.setVersion(Number(e.target.value))}
                  value={editState.version}
                >
                  {editState.minuteVersions.map((version, index) => {
                    const versionDate = new Date(
                      version.created_datetime
                    ).toLocaleDateString('en-GB', {
                      day: 'numeric',
                      month: 'short',
                      hour: 'numeric',
                      minute: 'numeric',
                    })
                    return (
                      <option value={`${index}`} key={version.id}>
                        {version.content_source === 'ai_edit' && 'AI edit'}
                        {version.content_source === 'manual_edit' && 'edit'}
                        {version.content_source === 'initial_generation' &&
                          'Initial'}{' '}
                        - {versionDate}
                      </option>
                    )
                  })}
                </select>
              </div>
              <div className="govuk-button-group !items-end">
                <AiEditPopover
                  minuteId={editState.minuteId}
                  minuteVersionId={editState.minuteVersionId}
                  onSuccess={editState.onSuccess}
                />
                <button
                  type="button"
                  className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0"
                  onClick={handleDiscard}
                >
                  Discard
                </button>
                <button
                  type="button"
                  className="govuk-button govuk-!-margin-bottom-0"
                  onClick={handleSave}
                >
                  <Save className="size-4" /> Save
                </button>
              </div>
            </div>
          )}
        </div>
        {editState?.isEditable ? (
          <form
            className="govuk-form-group govuk-!-margin-bottom-6"
            onSubmit={(e) => {
              e.preventDefault()
              handleSave()
            }}
          >
            <h1 className="govuk-label-wrapper">
              <label
                className="govuk-label govuk-label--m"
                htmlFor="transcription-title"
              >
                Transcription title
              </label>
            </h1>
            <input
              id="transcription-title"
              className="govuk-input"
              type="text"
              placeholder="Add title"
              value={draftTitle}
              onChange={(e) => setDraftTitle(e.target.value)}
            />
          </form>
        ) : (
          <h1 className="govuk-heading-l govuk-!-margin-bottom-2">
            {transcription.title}
          </h1>
        )}
        {!minute ? (
          <p className="govuk-body">Summary not found.</p>
        ) : (
          <>
            <div className="govuk-grid-row">
              <div className="govuk-grid-column-full">
                <MinuteEditor
                  key={minute.id}
                  transcription={transcription}
                  minute={minute}
                  onExportStateChange={setExportState}
                  onEditStateChange={setEditState}
                />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
