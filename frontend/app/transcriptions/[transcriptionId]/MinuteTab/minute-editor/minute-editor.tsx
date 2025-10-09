'use client'

import SimpleEditor from '@/app/transcriptions/[transcriptionId]/MinuteTab/components/editor/tiptap-editor'
import { RatingButton } from '@/app/transcriptions/[transcriptionId]/MinuteTab/components/rating-dialog/rating-dialog'
import { AiEditPopover } from '@/app/transcriptions/[transcriptionId]/MinuteTab/minute-editor/ai-edit-popover'
import { MinuteVersionSelect } from '@/app/transcriptions/[transcriptionId]/MinuteTab/minute-editor/minute-version-select'
import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
import { Button } from '@/components/ui/button'
import CopyButton from '@/components/ui/copy-button'
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
import convertAIMinutesToWordDoc from '@/lib/download-word-doc'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Download,
  Edit,
  Eye,
  EyeOff,
  FilePenLine,
  FileQuestion,
  FileX2,
  Loader2,
  Save,
  Undo,
} from 'lucide-react'
import posthog from 'posthog-js'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'

type MinuteEditorForm = {
  html: string
}

export function MinuteEditor({
  transcription,
  minute,
}: {
  transcription: Transcription
  minute: MinuteListItem
}) {
  const [version, setVersion] = useState(0)
  const [hideCitations, setHideCitations] = useState(false)
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
    return htmlContent?.replaceAll(/\s?\[(\d+)\]/g, '') || ''
  }, [htmlContent])
  const hasCitations = useMemo(() => {
    return !!htmlContent?.match(/\[(\d+)\]/)
  }, [htmlContent])
  useEffect(() => {}, [htmlContent])
  const { mutate: saveEdit } = useMutation({
    ...createMinuteVersionMinutesMinuteIdVersionsPostMutation(),
  })

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
  const handleWordDocDownload = useCallback(() => {
    posthog.capture('minutes_downloaded', {
      format: 'word',
      version_id: minuteVersion?.id,
    })

    convertAIMinutesToWordDoc(
      htmlContent,
      transcription.dialogue_entries || [],
      transcription.title || 'minutes.docx'
    )
  }, [
    htmlContent,
    minuteVersion?.id,
    transcription.dialogue_entries,
    transcription.title,
  ])

  if (isLoading) {
    return (
      <div className="flex flex-col items-center">
        <p>Loading...</p>
      </div>
    )
  }

  if (!minuteVersion) {
    return (
      <div className="flex flex-col items-center gap-2">
        <FileQuestion />
        <p>
          Nothing has been generated for this &quot;{minute.template_name}&quot;
          minute yet. Click below to generate a minute.
        </p>
        <NewMinuteDialog
          transcriptionId={transcription.id!}
          agenda={minute.agenda ?? undefined}
        />
      </div>
    )
  }
  if (isGenerating) {
    return (
      <div className="pt-2">
        <div className="mb-2 flex flex-wrap justify-between gap-y-2">
          <div className="flex flex-wrap gap-2">
            <MinuteVersionSelect
              minuteVersions={minuteVersions}
              version={version}
              setVersion={setVersion}
            />
          </div>
        </div>
        <div className="flex h-36 animate-pulse flex-col items-center justify-center pt-12">
          <FilePenLine />
          Minute generating...
        </div>
      </div>
    )
  }
  if (isError) {
    return (
      <div className="pt-2">
        <div className="mb-2 flex flex-wrap justify-between gap-y-2">
          <div className="flex flex-wrap gap-2">
            <MinuteVersionSelect
              minuteVersions={minuteVersions}
              version={version}
              setVersion={setVersion}
            />
          </div>
        </div>
        <div className="mx-auto flex flex-col items-center justify-center pt-12 text-center">
          <FileX2 />
          <p>There was a problem processing your request.</p>
          {minuteVersions.length > 1 ? (
            <>
              <p>Click undo to go back to the previous version.</p>
              <MinuteVersionDeleteButton minuteVersion={minuteVersion} />
            </>
          ) : (
            <>
              <p>Try generating a new Minute</p>
              <NewMinuteDialog
                transcriptionId={transcription.id!}
                agenda={minute.agenda ?? undefined}
              />
            </>
          )}
        </div>
      </div>
    )
  }
  return (
    <div className="pt-2">
      <div className="mb-2 flex flex-wrap justify-between gap-y-2">
        <div className="flex flex-wrap gap-2">
          <MinuteVersionSelect
            minuteVersions={minuteVersions}
            version={version}
            setVersion={setVersion}
          />
          <AiEditPopover
            disabled={isEditable}
            minuteId={minute.id!}
            minuteVersionId={minuteVersion.id}
            onSuccess={onSuccess}
          />
          {isEditable ? (
            <Button
              className="bg-blue-600 hover:bg-blue-800 active:bg-yellow-500"
              onClick={form.handleSubmit(onSubmit)}
            >
              <Save /> Save Changes
            </Button>
          ) : (
            <Button
              className="bg-blue-600 hover:bg-blue-800 active:bg-yellow-500"
              onClick={() => setIsEditable(true)}
              type="button"
            >
              <Edit />
              Edit Manually
            </Button>
          )}
          <Button
            type="button"
            className="bg-green-600 text-white hover:bg-green-700 active:bg-yellow-500"
            onClick={handleWordDocDownload}
          >
            <Download />
            Download
          </Button>
          <CopyButton
            textToCopy={contentToCopy}
            posthogEvent="editor_content_copied"
          />
          {hasCitations && (
            <Button
              variant="outline"
              onClick={() => setHideCitations((h) => !h)}
              disabled={isEditable}
            >
              {isEditable ? (
                'Citations shown when editing'
              ) : hideCitations ? (
                <>
                  <Eye /> Show Citations
                </>
              ) : (
                <>
                  <EyeOff />
                  Hide Citations
                </>
              )}
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          <RatingButton
            minuteVersionId={minuteVersion.id}
            minutes={minuteVersion.html_content}
            transcript={transcription.dialogue_entries!}
          />
        </div>
      </div>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <Controller
          control={form.control}
          name="html"
          render={({ field: { onChange } }) => (
            <SimpleEditor
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
          <Loader2 className="animate-spin" /> Deleting
        </>
      ) : (
        <>
          <Undo /> Undo
        </>
      )}
    </Button>
  )
}
