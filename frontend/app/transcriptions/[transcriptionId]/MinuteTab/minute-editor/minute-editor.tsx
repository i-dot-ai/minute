'use client'

import SimpleEditor from '@/app/transcriptions/[transcriptionId]/MinuteTab/components/editor/tiptap-editor'
import { ProcessingCard } from '@/components/processing-card'
import { Button } from '@/components/ui/button'
import { citationRegex, citationRegexWithSpace } from '@/lib/citationRegex'
import {
  MinuteListItem,
  MinuteVersionResponse,
  Transcription,
} from '@/lib/client'
import {
  createMinuteVersionMinutesMinuteIdVersionsPostMutation,
  deleteMinuteVersionMinuteVersionsMinuteVersionIdDeleteMutation,
  listMinuteVersionsMinutesMinuteIdVersionsGetOptions,
  listMinuteVersionsMinutesMinuteIdVersionsGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileX2, Loader2, Undo } from 'lucide-react'
import posthog from 'posthog-js'
import {
  Dispatch,
  SetStateAction,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { Controller, useForm } from 'react-hook-form'

type MinuteEditorForm = {
  html: string
}

// Generating a summary is a single pass over an existing transcript, so it is
// far quicker than transcribing the audio in the first place.
const SUMMARY_MINUTES_PER_AUDIO_MINUTE = 0.05
const SUMMARY_MINIMUM_ESTIMATE_MINUTES = 1

const getSummaryEstimateMinutes = (durationSec: number | undefined) =>
  durationSec
    ? Math.max(
        SUMMARY_MINIMUM_ESTIMATE_MINUTES,
        Math.round((durationSec / 60) * SUMMARY_MINUTES_PER_AUDIO_MINUTE)
      )
    : null

export type MinuteExportState = {
  htmlContent: string
  contentToCopy: string
  minuteVersionId: string
}

export type MinuteEditState = {
  minuteVersions: MinuteVersionResponse[]
  version: number
  setVersion: Dispatch<SetStateAction<number>>
  minuteId: string
  minuteVersionId: string
  minuteVersionHtml: string
  showEditActions: boolean
  isEditable: boolean
  setIsEditable: (editable: boolean) => void
  hasCitations: boolean
  hideCitations: boolean
  toggleHideCitations: () => void
  onSuccess: () => void
  onSave: () => void
  onCancel: () => void
}

export function MinuteEditor({
  transcription,
  minute,
  onExportStateChange,
  onEditStateChange,
}: {
  transcription: Transcription
  minute: MinuteListItem
  onExportStateChange?: (state: MinuteExportState | null) => void
  onEditStateChange?: (state: MinuteEditState | null) => void
}) {
  const [version, setVersion] = useState(0)
  const [hideCitations, setHideCitations] = useState(false)
  const [editorResetKey, setEditorResetKey] = useState(0)
  // Snapshot of the version history taken when edit mode starts, so Discard
  // can remove any versions created during the session and restore the
  // previous selection.
  const [editBaseline, setEditBaseline] = useState<{
    versionIds: string[]
    selectedVersionId: string
  } | null>(null)
  const { data: minuteVersions = [], isLoading } = useQuery({
    ...listMinuteVersionsMinutesMinuteIdVersionsGetOptions({
      path: { minute_id: minute.id! },
    }),
    refetchInterval: (query) =>
      query.state.data &&
      query.state.data.length > 0 &&
      ['awaiting_start', 'in_progress'].includes(
        query.state.data[version].status
      )
        ? 1000
        : false,
  })
  const minuteVersion = useMemo(
    () => (minuteVersions.length > 0 ? minuteVersions[version] : undefined),
    [minuteVersions, version]
  )
  const isGenerating = useMemo(
    () =>
      ['awaiting_start', 'in_progress'].includes(minuteVersion?.status || ''),
    [minuteVersion?.status]
  )
  const isError = useMemo(
    () => minuteVersion?.status == 'failed',
    [minuteVersion?.status]
  )

  const queryClient = useQueryClient()
  const [isEditable, setIsEditable] = useState(false)
  const form = useForm<MinuteEditorForm>()
  useEffect(() => {
    if (minuteVersion) {
      form.setValue('html', minuteVersion.html_content)
    }
  }, [form, minuteVersion])
  const htmlContent = form.watch('html')
  const contentToCopy = useMemo(() => {
    return htmlContent?.replaceAll(citationRegexWithSpace, '') || ''
  }, [htmlContent])
  const hasCitations = useMemo(() => {
    return !!htmlContent?.match(citationRegex)
  }, [htmlContent])
  const toggleHideCitations = useCallback(() => {
    setHideCitations((h) => !h)
  }, [])
  const { mutate: saveEdit } = useMutation({
    ...createMinuteVersionMinutesMinuteIdVersionsPostMutation(),
  })
  const { mutateAsync: deleteVersion } = useMutation({
    ...deleteMinuteVersionMinuteVersionsMinuteVersionIdDeleteMutation(),
  })

  const startEditing = useCallback(
    (editable: boolean) => {
      if (editable && minuteVersion) {
        setEditBaseline({
          versionIds: minuteVersions.map((v) => v.id!),
          selectedVersionId: minuteVersion.id!,
        })
      }
      setIsEditable(editable)
    },
    [minuteVersion, minuteVersions]
  )

  const onSuccess = useCallback(() => {
    setIsEditable(false)
    setVersion(0)
    queryClient.invalidateQueries({
      queryKey: listMinuteVersionsMinutesMinuteIdVersionsGetQueryKey({
        path: { minute_id: minute.id! },
      }),
    })
  }, [minute.id, queryClient])

  const onSubmit = useCallback(
    (data: MinuteEditorForm) => {
      setEditBaseline(null)
      if (data.html != minuteVersion?.html_content) {
        saveEdit(
          {
            path: { minute_id: minute.id! },
            body: { html_content: data.html, content_source: 'manual_edit' },
          },
          {
            onSuccess,
          }
        )
      }
      {
        setIsEditable(false)
      }
    },
    [minute.id, minuteVersion?.html_content, onSuccess, saveEdit]
  )
  const onCancel = useCallback(async () => {
    const baseline = editBaseline
    setEditBaseline(null)
    setIsEditable(false)
    setEditorResetKey((key) => key + 1)
    if (!baseline) {
      form.setValue('html', minuteVersion?.html_content || '')
      return
    }
    // Restore the selection made before editing started. Versions created
    // during the session are all newer than the baseline, so once they are
    // deleted the baseline indices are valid again.
    setVersion(
      Math.max(0, baseline.versionIds.indexOf(baseline.selectedVersionId))
    )
    const createdDuringEdit = minuteVersions.filter(
      (v) => !baseline.versionIds.includes(v.id!)
    )
    if (createdDuringEdit.length > 0) {
      await Promise.allSettled(
        createdDuringEdit.map((v) =>
          deleteVersion({ path: { minute_version_id: v.id! } })
        )
      )
      queryClient.invalidateQueries({
        queryKey: listMinuteVersionsMinutesMinuteIdVersionsGetQueryKey({
          path: { minute_id: minute.id! },
        }),
      })
    } else {
      form.setValue('html', minuteVersion?.html_content || '')
    }
  }, [
    deleteVersion,
    editBaseline,
    form,
    minute.id,
    minuteVersion?.html_content,
    minuteVersions,
    queryClient,
  ])
  useEffect(() => {
    if (!onExportStateChange) return
    if (!minuteVersion || isGenerating || isError) {
      onExportStateChange(null)
      return
    }
    onExportStateChange({
      htmlContent: htmlContent || '',
      contentToCopy,
      minuteVersionId: minuteVersion.id!,
    })
  }, [
    contentToCopy,
    htmlContent,
    isError,
    isGenerating,
    minuteVersion,
    onExportStateChange,
  ])
  useEffect(() => {
    if (!onEditStateChange) return
    if (!minuteVersion || isGenerating) {
      onEditStateChange(null)
      return
    }
    if (isError) {
      onEditStateChange({
        minuteVersions,
        version,
        setVersion,
        minuteId: minute.id!,
        minuteVersionId: minuteVersion.id!,
        minuteVersionHtml: minuteVersion.html_content || '',
        showEditActions: false,
        isEditable: false,
        setIsEditable: () => {},
        hasCitations: false,
        hideCitations: false,
        toggleHideCitations: () => {},
        onSuccess,
        onSave: () => {},
        onCancel: () => {},
      })
      return
    }
    onEditStateChange({
      minuteVersions,
      version,
      setVersion,
      minuteId: minute.id!,
      minuteVersionId: minuteVersion.id!,
      minuteVersionHtml: minuteVersion.html_content || '',
      showEditActions: true,
      isEditable,
      setIsEditable: startEditing,
      hasCitations,
      hideCitations,
      toggleHideCitations,
      onSuccess,
      onSave: form.handleSubmit(onSubmit),
      onCancel,
    })
  }, [
    form,
    hasCitations,
    hideCitations,
    isEditable,
    isError,
    isGenerating,
    minute.id,
    minuteVersion,
    minuteVersions,
    onCancel,
    onEditStateChange,
    onSubmit,
    onSuccess,
    startEditing,
    toggleHideCitations,
    version,
  ])
  if (isLoading) {
    return (
      <div className="flex items-center gap-2">
        <Loader2 className="size-4 animate-spin" />
        <p className="govuk-body govuk-!-margin-bottom-0">Loading...</p>
      </div>
    )
  }

  if (!minuteVersion) {
    return (
      <>
        <p className="govuk-body">
          Nothing has been generated for this &quot;{minute.template_name}&quot;
          minute yet. Generate a new minute from the panel to the left.
        </p>
      </>
    )
  }
  if (isGenerating) {
    return (
      <ProcessingCard
        className="govuk-!-margin-top-2"
        heading="Generating summary"
        estimatedMinutes={getSummaryEstimateMinutes(
          transcription.dialogue_entries?.at(-1)?.end_time
        )}
      />
    )
  }
  if (isError) {
    return (
      <div className="flex items-center gap-2">
        <FileX2 className="size-4" />
        <p className="govuk-body">
          There was a problem processing your request.
        </p>
        {true ? (
          <>
            <p>Click undo to go back to the previous version.</p>
            <MinuteVersionDeleteButton minuteVersion={minuteVersion} />
          </>
        ) : (
          <>
            <p className="govuk-body">
              Generate a new minute from the panel to the left.
            </p>
          </>
        )}
      </div>
    )
  }
  return (
    <div>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <Controller
          control={form.control}
          name="html"
          render={({ field: { onChange } }) => (
            <SimpleEditor
              key={`${minuteVersion.id}-${editorResetKey}`}
              currentTranscription={transcription}
              initialContent={minuteVersion.html_content || ''}
              isEditing={isEditable}
              onContentChange={onChange}
              hideCitations={hideCitations && !isEditable}
            />
          )}
        />
      </form>
    </div>
  )
}

const MinuteVersionDeleteButton = ({
  minuteVersion,
  className,
}: {
  minuteVersion: MinuteVersionResponse
  className?: string
}) => {
  const queryClient = useQueryClient()
  const { mutate, isPending } = useMutation({
    ...deleteMinuteVersionMinuteVersionsMinuteVersionIdDeleteMutation(),
    onSuccess() {
      queryClient.invalidateQueries({
        queryKey: listMinuteVersionsMinutesMinuteIdVersionsGetQueryKey({
          path: { minute_id: minuteVersion.minute_id },
        }),
      })
      posthog.capture('deleted_minute_version', {
        minuteVersionId: minuteVersion.id,
      })
    },
  })
  return (
    <Button
      variant="outline"
      onClick={() => mutate({ path: { minute_version_id: minuteVersion.id } })}
      className={className}
    >
      {isPending ? (
        <>
          <Loader2 className="size-4 animate-spin" /> Deleting
        </>
      ) : (
        <>
          <Undo className="size-4" /> Undo
        </>
      )}
    </Button>
  )
}
