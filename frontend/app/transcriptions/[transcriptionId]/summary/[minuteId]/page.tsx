'use client'

import { AiEditPopover } from '@/app/transcriptions/[transcriptionId]/MinuteTab/minute-editor/ai-edit-popover'
import {
  MinuteEditState,
  MinuteEditor,
  MinuteExportState,
} from '@/app/transcriptions/[transcriptionId]/MinuteTab/minute-editor/minute-editor'
import { TranscriptionSidePanel } from '@/app/transcriptions/[transcriptionId]/MinuteTab/components/TranscriptionSidePanel'
import { DeleteTranscriptionButton } from '@/components/recent-meetings/delete-transcription-button'
import CopyButton from '@/components/ui/copy-button'
import {
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import convertAIMinutesToWordDoc from '@/lib/download-word-doc'
import { useQuery } from '@tanstack/react-query'
import {
  DownloadIcon,
  Eye,
  EyeOffIcon,
  Loader2,
  PencilIcon,
} from 'lucide-react'
import Link from 'next/link'
import posthog from 'posthog-js'
import { useCallback, useState } from 'react'

export default function SummaryPage({
  params: { transcriptionId, minuteId },
}: {
  params: { transcriptionId: string; minuteId: string }
}) {
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

  const [isEditing, setIsEditing] = useState(false)
  const [exportState, setExportState] = useState<MinuteExportState | null>(null)
  const [editState, setEditState] = useState<MinuteEditState | null>(null)

  const handleWordDocDownload = useCallback(() => {
    if (!exportState || !transcription) return
    posthog.capture('minutes_downloaded', {
      format: 'word',
      version_id: exportState.minuteVersionId,
    })

    convertAIMinutesToWordDoc(
      exportState.htmlContent,
      transcription.dialogue_entries || [],
      transcription.title || 'minutes.docx'
    )
  }, [exportState, transcription])

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
        <div className="flex justify-end">
          <div className="govuk-button-group transcription-page__actions">
            <button
              type="button"
              className="govuk-button govuk-button--secondary"
              onClick={() => setIsEditing(true)}
            >
              Edit
            </button>
            <button
              type="button"
              className="govuk-button govuk-button--secondary"
              disabled={isEditing}
            >
              Download
            </button>
            <button
              type="button"
              className="govuk-button govuk-button--secondary"
              disabled={isEditing}
            >
              Copy
            </button>
            <DeleteTranscriptionButton
              transcription={transcription}
              disabled={isEditing}
            />
          </div>
        </div>
        <h1 className="govuk-heading-l govuk-!-margin-bottom-2">
          {transcription.title}
        </h1>
        <p className="govuk-body">{date}</p>
        {!minute ? (
          <p className="govuk-body">Summary not found.</p>
        ) : (
          <>
            {editState && (
              <div className="border-b border-(--govuk-border-colour) bg-[#8eb8dc] px-[20px] pt-[30px] pb-[10px]">
                <div className="govuk-grid-row">
                  <div className="govuk-grid-column-one-half govuk-grid-column-one-third-from-desktop">
                    <div className="govuk-form-group govuk-!-margin-bottom-3">
                      <label className="govuk-label" htmlFor="version">
                        Choose an edit version
                      </label>
                      <select
                        disabled={editState.isEditable}
                        className="govuk-select w-full"
                        id="version"
                        name="version"
                        onChange={(e) =>
                          editState.setVersion(Number(e.target.value))
                        }
                        value={editState.version}
                      >
                        {editState.minuteVersions.map((version, index) => {
                          const versionDate = new Date(
                            version.created_datetime
                          ).toLocaleDateString('en-GB', {
                            day: 'numeric',
                            month: 'short',
                            year: '2-digit',
                            hour: 'numeric',
                            minute: 'numeric',
                          })
                          const versionNumber =
                            editState.minuteVersions.length - index
                          return (
                            <option value={`${index}`} key={version.id}>
                              {versionNumber} -{' '}
                              {version.content_source === 'ai_edit'
                                ? 'AI edited'
                                : 'Manually edited'}{' '}
                              - {versionDate}
                            </option>
                          )
                        })}
                      </select>
                    </div>
                  </div>
                  <div className="govuk-grid-column-one-half govuk-grid-column-two-thirds-from-desktop">
                    <div className="govuk-button-group govuk-!-margin-bottom-0 govuk-!-margin-top-6">
                      {editState.showEditActions && (
                        <>
                          <button
                            className="govuk-button govuk-button--inverse govuk-!-margin-bottom-3"
                            onClick={() => editState.setIsEditable(true)}
                            type="button"
                            disabled={editState.isEditable}
                          >
                            <PencilIcon className="size-4" /> Edit manually
                          </button>
                          <AiEditPopover
                            disabled={editState.isEditable}
                            minuteId={editState.minuteId}
                            minuteVersionId={editState.minuteVersionId}
                            onSuccess={editState.onSuccess}
                          />
                          {exportState && (
                            <>
                              <button
                                className="govuk-button govuk-button--inverse"
                                disabled={editState.isEditable}
                                onClick={handleWordDocDownload}
                              >
                                <DownloadIcon className="size-4" />
                                Download
                              </button>
                              <CopyButton
                                disabled={editState.isEditable}
                                textToCopy={exportState.contentToCopy}
                                posthogEvent="editor_content_copied"
                              />
                              {editState.hasCitations && (
                                <button
                                  className="govuk-button govuk-button--inverse"
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
                            </>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
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
