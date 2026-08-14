'use client'

import { AiEditPopover } from '@/app/transcriptions/[transcriptionId]/MinuteTab/minute-editor/ai-edit-popover'
import {
  MinuteEditState,
  MinuteEditor,
  MinuteExportState,
} from '@/app/transcriptions/[transcriptionId]/MinuteTab/minute-editor/minute-editor'
import { DeleteMinuteButton } from '@/app/transcriptions/[transcriptionId]/MinuteTab/components/delete-minute-button'
import { ExportSummaryDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/ExportSummaryDialog'
import {
  applySpeakerRenames,
  SpeakerEditorDialog,
  SpeakerRenames,
} from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/SpeakerEditor'
import { useRenameTranscription } from '@/components/recent-meetings/rename-transcription'
import { useGenerateSummaryFromMinute } from '@/hooks/use-generate-summary-from-minute'
import { useSaveTranscription } from '@/hooks/use-save-transcription'
import {
  getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions,
  getTranscriptionTranscriptionsTranscriptionIdGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import {
  Eye,
  EyeOffIcon,
  Loader2,
  PencilIcon,
  PlusIcon,
  Save,
  User,
  CircleArrowRight,
} from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { use, useCallback, useEffect, useState } from 'react'
import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'

export default function SummaryPage({
  params,
}: {
  params: Promise<{ transcriptionId: string; minuteId: string }>
}) {
  const { transcriptionId, minuteId } = use(params)
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

  const { data: recordings } = useQuery({
    ...getRecordingsForTranscriptionTranscriptionsTranscriptionIdRecordingsGetOptions(
      { path: { transcription_id: transcriptionId } }
    ),
  })

  const [exportState, setExportState] = useState<MinuteExportState | null>(null)
  const [editState, setEditState] = useState<MinuteEditState | null>(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [speakerEditorOpen, setSpeakerEditorOpen] = useState(false)
  const [isSavingSpeakers, setIsSavingSpeakers] = useState(false)

  const router = useRouter()
  const { saveTranscription } = useSaveTranscription(transcriptionId)
  const { generateSummary, isGenerating } =
    useGenerateSummaryFromMinute(transcriptionId)

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

  const handleSaveSpeakersAndGenerate = useCallback(
    async (renames: SpeakerRenames) => {
      if (!transcription?.dialogue_entries) return
      setIsSavingSpeakers(true)
      try {
        await saveTranscription({
          entries: applySpeakerRenames(transcription.dialogue_entries, renames),
        })
        const newMinute = await generateSummary(minuteId)
        setSpeakerEditorOpen(false)
        router.push(
          `/transcriptions/${transcriptionId}/summary/${newMinute.id}`
        )
      } catch {
        // keep dialog open so changes are not lost
      } finally {
        setIsSavingSpeakers(false)
      }
    },
    [
      generateSummary,
      minuteId,
      router,
      saveTranscription,
      transcription?.dialogue_entries,
      transcriptionId,
    ]
  )

  if (isLoading) {
    return (
      <div className="govuk-width-container govuk-!-padding-top-4 govuk-width-container--with-secondary-nav">
        <div className="flex items-center gap-2">
          <Loader2 className="animate-spin" />
          <p className="govuk-body govuk-!-margin-bottom-0">Loading...</p>
        </div>
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

  return (
    <div className="flex h-full flex-col">
      <div className="govuk-!-padding-top-4 shrink-0 border-b border-(--govuk-border-colour) bg-white">
        <div className="govuk-width-container govuk-width-container--with-secondary-nav">
          {!editState?.isEditable && (
            <div className="sm:flex sm:justify-between">
              <nav
                className="govuk-breadcrumbs govuk-!-margin-top-2 sm:mb-0"
                aria-label="Breadcrumb"
              >
                <ol className="govuk-breadcrumbs__list">
                  <li className="govuk-breadcrumbs__list-item">
                    <Link
                      className="govuk-breadcrumbs__link"
                      href="/transcriptions"
                    >
                      Back
                    </Link>
                  </li>
                </ol>
              </nav>
              <div className="govuk-button-group govuk-!-margin-bottom-0 justify-end">
                <Link
                  href={`/transcriptions/${transcriptionId}/transcript`}
                  className="govuk-button sm:!hidden"
                >
                  <CircleArrowRight className="size-4" /> Go to transcript
                </Link>
                <NewMinuteDialog
                  transcriptionId={transcriptionId}
                  icon
                  buttonClassName="govuk-button govuk-button--secondary sm:!hidden"
                  onCreated={() =>
                    router.push(`/transcriptions/${transcriptionId}/summary`)
                  }
                />
                {editState && (
                  <>
                    {editState.hasCitations && (
                      <button
                        className="govuk-button govuk-button--secondary min-w-48"
                        onClick={editState.toggleHideCitations}
                        disabled={editState.isEditable}
                        id="tour-show-references"
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
                    <ExportSummaryDialog
                      exportState={exportState}
                      title={transcription.title}
                      dialogueEntries={transcription.dialogue_entries}
                      disabled={editState.isEditable}
                    />
                    <button
                      className="govuk-button !hidden sm:!flex"
                      onClick={() => editState.setIsEditable(true)}
                      type="button"
                      disabled={editState.isEditable}
                      id="tour-edit-summary"
                    >
                      <PencilIcon className="size-4" /> Edit
                    </button>
                    <button
                      className="govuk-button govuk-button--secondary sm:!hidden"
                      onClick={() => editState.setIsEditable(true)}
                      type="button"
                      disabled={editState.isEditable}
                      id="tour-edit-summary"
                    >
                      <PencilIcon className="size-4" /> Edit
                    </button>
                  </>
                )}
                {minute && (
                  <DeleteMinuteButton
                    minute={minute}
                    transcriptionId={transcriptionId}
                  />
                )}
              </div>
            </div>
          )}
          {editState && editState.isEditable && (
            <div className="flex flex-col justify-between lg:flex-row">
              <div className="govuk-form-group govuk-!-margin-bottom-3 flex items-center gap-2">
                <label className="govuk-label" htmlFor="version">
                  Version history
                </label>
                <select
                  className="govuk-select"
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
                <button
                  type="button"
                  className="govuk-button govuk-button--secondary sm:mb-0"
                  onClick={() => setSpeakerEditorOpen(true)}
                >
                  <User className="size-4" />
                  Edit all speaker names
                </button>
                <SpeakerEditorDialog
                  entries={transcription.dialogue_entries ?? []}
                  src={recordings?.length ? recordings[0].url : undefined}
                  open={speakerEditorOpen}
                  onOpenChange={setSpeakerEditorOpen}
                  description="This will update the transcript and generate a new summary using this summary's template."
                  isBusy={isSavingSpeakers || isGenerating}
                  onSaveAndGenerate={handleSaveSpeakersAndGenerate}
                  cancelLabel="Close"
                />
                <AiEditPopover
                  minuteId={editState.minuteId}
                  minuteVersionId={editState.minuteVersionId}
                  onSuccess={editState.onSuccess}
                />
                <button
                  type="button"
                  className="govuk-button govuk-button--secondary sm:mb-0"
                  onClick={handleDiscard}
                >
                  Discard
                </button>
                <button
                  type="button"
                  className="govuk-button sm:mb-0"
                  onClick={handleSave}
                >
                  <Save className="size-4" /> Save
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      <div
        className={`min-h-0 flex-1 overflow-y-auto ${
          editState?.isEditable
            ? 'govuk-!-padding-4 bg-(--govuk-surface-background-colour)'
            : ''
        }`}
      >
        <div
          className="govuk-width-container govuk-width-container--with-secondary-nav"
          id="tour-summary"
        >
          {editState?.isEditable ? (
            <form
              className="govuk-form-group govuk-!-margin-bottom-6 govuk-!-margin-top-4"
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
                className="govuk-input bg-white"
                type="text"
                placeholder="Add title"
                value={draftTitle}
                onChange={(e) => setDraftTitle(e.target.value)}
              />
            </form>
          ) : (
            <h1 className="govuk-heading-l govuk-!-margin-top-4">
              {transcription.title}
            </h1>
          )}
          {!minute ? (
            <p className="govuk-body">Summary not found.</p>
          ) : (
            <>
              <div className="govuk-grid-row">
                <div className="govuk-grid-column-full govuk-!-margin-bottom-8">
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
    </div>
  )
}
