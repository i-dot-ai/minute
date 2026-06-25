'use client'

import { AiEditPopover } from '@/app/transcriptions/[transcriptionId]/MinuteTab/minute-editor/ai-edit-popover'
import {
  MinuteEditState,
  MinuteEditor,
  MinuteExportState,
} from '@/app/transcriptions/[transcriptionId]/MinuteTab/minute-editor/minute-editor'
import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
import CopyButton from '@/components/ui/copy-button'
import { MinuteListItem, Transcription } from '@/lib/client'
import convertAIMinutesToWordDoc from '@/lib/download-word-doc'
import {
  AudioWaveform,
  DownloadIcon,
  Eye,
  EyeOffIcon,
  PencilIcon,
} from 'lucide-react'
import posthog from 'posthog-js'
import { useCallback, useEffect, useState } from 'react'

export function MinuteTab({
  transcription,
  minutes,
}: {
  transcription: Transcription
  minutes: MinuteListItem[]
}) {
  const [selectedMinute, setSelectedMinute] = useState(0)
  const [exportState, setExportState] = useState<MinuteExportState | null>(null)
  const [editState, setEditState] = useState<MinuteEditState | null>(null)

  useEffect(() => {
    setSelectedMinute(0)
  }, [minutes])

  useEffect(() => {
    setExportState(null)
    setEditState(null)
  }, [selectedMinute])

  const handleWordDocDownload = useCallback(() => {
    if (!exportState) return
    posthog.capture('minutes_downloaded', {
      format: 'word',
      version_id: exportState.minuteVersionId,
    })

    convertAIMinutesToWordDoc(
      exportState.htmlContent,
      transcription.dialogue_entries || [],
      transcription.title || 'minutes.docx'
    )
  }, [exportState, transcription.dialogue_entries, transcription.title])

  if (minutes.length == 0) {
    return (
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <AudioWaveform className="size-4" />
          <p>No minutes generated yet.</p>
          <div>
            <NewMinuteDialog transcriptionId={transcription.id!} />
          </div>
        </div>
      </div>
    )
  }
  return (
    <>
      <div className="border-b border-(--govuk-border-colour) bg-[#8eb8dc] px-[20px] pt-[30px] pb-[10px] sm:mx-[-20px] sm:mt-[-30px]">
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-one-half govuk-grid-column-one-third-from-desktop">
            <div className="govuk-form-group govuk-!-margin-bottom-2">
              <label className="govuk-label" htmlFor="summary-history">
                Choose a summary
              </label>
              <select
                className="govuk-select w-full"
                id="summary-history"
                name="summary-history"
                disabled={editState ? editState.isEditable : false}
                onChange={(e) => setSelectedMinute(Number(e.target.value))}
                value={selectedMinute}
              >
                {minutes.map((minute, index) => {
                  const date = new Date(
                    minute.updated_datetime
                  ).toLocaleDateString('en-GB', {
                    day: 'numeric',
                    month: 'short',
                    year: '2-digit',
                    hour: 'numeric',
                    minute: 'numeric',
                  })
                  return (
                    <option value={`${index}`} key={minute.id}>
                      {minute.template_name} - {date}
                    </option>
                  )
                })}
              </select>
            </div>
          </div>
          <div className="govuk-grid-column-one-half govuk-grid-column-two-thirds-from-desktop">
            <NewMinuteDialog
              disabled={editState ? editState.isEditable : false}
              transcriptionId={transcription.id!}
              agenda={minutes[selectedMinute]?.agenda ?? undefined}
            />
          </div>
        </div>
        {editState && (
          <>
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
                      const date = new Date(
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
                          - {date}
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
                            disabled={editState ? editState.isEditable : false}
                            onClick={handleWordDocDownload}
                          >
                            <DownloadIcon className="size-4" />
                            Download
                          </button>
                          <CopyButton
                            disabled={editState ? editState.isEditable : false}
                            textToCopy={exportState.contentToCopy}
                            posthogEvent="editor_content_copied"
                          />
                          {editState && editState.hasCitations && (
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
          </>
        )}
      </div>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-full">
          <MinuteEditor
            key={minutes[selectedMinute].id}
            transcription={transcription}
            minute={minutes[selectedMinute]}
            onExportStateChange={setExportState}
            onEditStateChange={setEditState}
          />
        </div>
      </div>
    </>
  )
}
