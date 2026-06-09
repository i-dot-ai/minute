'use client'

import { RatingButton } from '@/app/transcriptions/[transcriptionId]/MinuteTab/components/rating-dialog/rating-dialog'
import { AiEditPopover } from '@/app/transcriptions/[transcriptionId]/MinuteTab/minute-editor/ai-edit-popover'
import {
  MinuteEditState,
  MinuteEditor,
  MinuteExportState,
} from '@/app/transcriptions/[transcriptionId]/MinuteTab/minute-editor/minute-editor'
import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
import { AudioWav } from '@/components/icons/AudioWav'
import CopyButton from '@/components/ui/copy-button'
import { Transcription } from '@/lib/client'
import { listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import convertAIMinutesToWordDoc from '@/lib/download-word-doc'
import { useQuery } from '@tanstack/react-query'
import { AudioWaveform } from 'lucide-react'
import posthog from 'posthog-js'
import { useCallback, useEffect, useState } from 'react'

export function MinuteTab({ transcription }: { transcription: Transcription }) {
  const { data: minutes = [], isLoading } = useQuery({
    ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions(
      {
        path: { transcription_id: transcription.id! },
      }
    ),
  })
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
  }, [
    exportState,
    transcription.dialogue_entries,
    transcription.title,
  ])

  if (isLoading) {
    return (
      <div className="flex w-full flex-col items-center justify-center">
        <AudioWav />
      </div>
    )
  }
  if (minutes.length == 0) {
    return (
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <AudioWaveform />
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
      <div className="govuk-grid-row">
        <div className="side-panel__sticky-container govuk-grid-column-one-third">
          <h2 className="govuk-heading-m">Export</h2>
          {exportState && (
            <div className="govuk-button-group">
              <div className="flex flex-wrap gap-2">
                <button
                  className="govuk-button govuk-button--secondary"
                  onClick={handleWordDocDownload}
                >
                  Download word doc
                </button>
                <CopyButton
                  textToCopy={exportState.contentToCopy}
                  posthogEvent="editor_content_copied"
                />
              </div>
            </div>
          )}
          <div className="side-panel__section-divider" />

          <h2 className="govuk-heading-m">Summaries</h2>
          <div className="govuk-form-group govuk-!-margin-bottom-2">
            <label className="govuk-label" htmlFor="sort">
              Choose a summary
            </label>
            <select className="govuk-select" id="summary-history" name="summary-history" onChange={(e) => setSelectedMinute(Number(e.target.value))} value={selectedMinute}>
              {minutes.map((minute, index) => {
                const date = new Date(minute.updated_datetime).toLocaleDateString('en-GB', { day: 'numeric', month: 'numeric', year: 'numeric', hour: 'numeric', minute: 'numeric' })
                return (
                  <option value={`${index}`} key={minute.id}>
                    {minute.template_name} - {date}
                  </option>
                )
              })}
            </select>
          </div>
          <NewMinuteDialog
            transcriptionId={transcription.id!}
            agenda={minutes[selectedMinute].agenda ?? undefined}
          />
          <div className="side-panel__section-divider" />


          {editState && (
            <>
              <h2 className="govuk-heading-m">Edit</h2>
              <div className="govuk-form-group">
                <label className="govuk-label" htmlFor="version">
                  Choose an edit version
                </label>
                <select className="govuk-select" id="version" name="version" onChange={(e) => editState.setVersion(Number(e.target.value))} value={editState.version}>
                  {editState.minuteVersions.map((version, index) => {
                    const date = new Date(version.created_datetime).toLocaleDateString('en-GB', { day: 'numeric', month: 'numeric', year: 'numeric', hour: 'numeric', minute: 'numeric' })
                    const versionNumber = editState.minuteVersions.length - index;
                    return (
                      <option value={`${index}`} key={version.id}>
                        {versionNumber} - {version.content_source === 'ai_edit' ? 'AI edited' : 'Manually edited'} - {date}
                      </option>
                    )
                  })}
                </select>
                {editState.showEditActions && (
                  <div className="govuk-button-group govuk-!-margin-top-2">
                    <AiEditPopover
                      disabled={editState.isEditable}
                      minuteId={editState.minuteId}
                      minuteVersionId={editState.minuteVersionId}
                      onSuccess={editState.onSuccess}
                    />
                    <button
                      className="govuk-button govuk-button--secondary"
                      onClick={() => editState.setIsEditable(true)}
                      type="button"
                      disabled={editState.isEditable}
                    >
                      Edit Manually
                    </button>
                    {editState.isEditable && (
                      <button
                        className="govuk-button govuk-button--secondary"
                        onClick={editState.onSave}
                      >
                        Save Changes
                      </button>
                    )}
                  </div>
                )}
              </div>

              {editState.showEditActions && (
                <>
                  {editState.hasCitations && (
                    <>
                      <div className="side-panel__section-divider" />
                      <h2 className="govuk-heading-m">View controls</h2>
                      <div className="govuk-form-group govuk-!-margin-bottom-2">
                        <button
                          className="govuk-button govuk-button--secondary"
                          onClick={editState.toggleHideCitations}
                          disabled={editState.isEditable}
                        >
                          {editState.hideCitations ? 'Show citations' : 'Hide citations'}
                        </button>
                      </div>
                    </>
                  )}
                </>
              )}
            </>
          )}
        </div>
        <div className="govuk-grid-column-two-thirds" style={{ borderLeft: '1px solid #b1b4b6' }}>
          <MinuteEditor
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
