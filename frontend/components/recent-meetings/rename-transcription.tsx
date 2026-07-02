'use client'

import { JobStatus } from '@/lib/client'
import {
  getTranscriptionTranscriptionsTranscriptionIdGetQueryKey,
  listTranscriptionsTranscriptionsGetQueryKey,
  saveTranscriptionTranscriptionsTranscriptionIdPatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { PencilIcon } from 'lucide-react'
import posthog from 'posthog-js'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'

export type RenameTranscription = {
  id: string
  title?: string | null
  status: JobStatus
}

export function getTranscriptionDisplayTitle(
  title: string | null | undefined,
  status: JobStatus
) {
  return (
    title ||
    (['awaiting_start', 'in_progress'].includes(status)
      ? 'Generating title'
      : 'No title')
  )
}

export function useRenameTranscription(transcription: RenameTranscription) {
  const queryClient = useQueryClient()

  const { mutate: saveTranscription, isPending } = useMutation({
    ...saveTranscriptionTranscriptionsTranscriptionIdPatchMutation(),
    onSuccess() {
      queryClient.invalidateQueries({
        queryKey: listTranscriptionsTranscriptionsGetQueryKey(),
      })
      queryClient.invalidateQueries({
        queryKey: getTranscriptionTranscriptionsTranscriptionIdGetQueryKey({
          path: { transcription_id: transcription.id },
        }),
      })
      posthog.capture('edited_transcript_title', {
        transcriptionId: transcription.id,
      })
    },
  })

  const save = useCallback(
    (title: string) => {
      const newTitle = title.trim() || null
      const currentTitle = transcription.title?.trim() || null
      if (newTitle === currentTitle) return
      saveTranscription({
        path: { transcription_id: transcription.id },
        body: { title: newTitle },
      })
    },
    [saveTranscription, transcription.id, transcription.title]
  )

  return { save, isPending }
}

export function RenameButton({
  displayTitle,
  disabled,
  onClick,
}: {
  displayTitle: string
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      data-module="govuk-button"
      className="govuk-link shrink-0 text-(--govuk-link-colour) govuk-!-margin-bottom-0 hover:cursor-pointer"
      onClick={onClick}
      disabled={disabled}
      aria-label={`Rename ${displayTitle}`}
    >
      <PencilIcon className="size-4" aria-hidden="true" />
      <span className="govuk-visually-hidden">Rename {displayTitle}</span>
    </button>
  )
}

export function RenameTitleInput({
  transcription,
  isPending,
  onSubmit,
  onCancel,
}: {
  transcription: RenameTranscription
  isPending: boolean
  onSubmit: (title: string) => void
  onCancel: () => void
}) {
  const skipBlurSaveRef = useRef(false)
  const inputId = `transcription-title-${transcription.id}`
  const hintId = `${inputId}-hint`
  const statusId = `${inputId}-status`

  const form = useForm<{ title: string }>({
    defaultValues: { title: transcription.title ?? '' },
  })

  const handleSubmit = useCallback(
    ({ title }: { title: string }) => {
      skipBlurSaveRef.current = true
      onSubmit(title)
    },
    [onSubmit]
  )

  const cancel = useCallback(() => {
    skipBlurSaveRef.current = true
    form.reset({ title: transcription.title ?? '' })
    onCancel()
  }, [form, onCancel, transcription.title])

  useEffect(() => {
    skipBlurSaveRef.current = false
    form.reset({ title: transcription.title ?? '' })
    form.setFocus('title', { shouldSelect: true })
  }, [form, transcription.title])

  return (
    <form
      onSubmit={form.handleSubmit(handleSubmit)}
      className="govuk-form-group govuk-!-margin-bottom-0 min-w-0 flex-1"
      aria-busy={isPending}
    >
      <label className="govuk-label govuk-visually-hidden" htmlFor={inputId}>
        Rename transcription
      </label>
      <input
        id={inputId}
        className="govuk-input govuk-!-margin-bottom-0 w-full"
        type="text"
        placeholder="Add title"
        disabled={isPending}
        aria-describedby={`${hintId} ${statusId}`}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            form.handleSubmit(handleSubmit)()
          }
          if (e.key === 'Escape') {
            e.preventDefault()
            cancel()
          }
        }}
        {...form.register('title', {
          onBlur: () => {
            if (skipBlurSaveRef.current) {
              skipBlurSaveRef.current = false
              return
            }
            form.handleSubmit(handleSubmit)()
          },
        })}
      />
      <span id={hintId} className="govuk-hint govuk-visually-hidden">
        Press Enter to save, Escape to cancel
      </span>
      <span id={statusId} className="govuk-visually-hidden" aria-live="polite">
        {isPending ? 'Saving title' : ''}
      </span>
    </form>
  )
}

export function RenameTranscriptionInline({
  transcription,
  headingLevel = 'h2',
  headingClassName = 'govuk-body govuk-!-margin-bottom-0',
}: {
  transcription: RenameTranscription
  headingLevel?: 'h1' | 'h2' | 'h3'
  headingClassName?: string
}) {
  const [editing, setEditing] = useState(false)
  const { save, isPending } = useRenameTranscription(transcription)
  const displayTitle = getTranscriptionDisplayTitle(
    transcription.title,
    transcription.status
  )

  const Heading = headingLevel

  const handleSubmit = useCallback(
    (title: string) => {
      save(title)
      setEditing(false)
    },
    [save]
  )

  if (editing) {
    return (
      <RenameTitleInput
        transcription={transcription}
        isPending={isPending}
        onSubmit={handleSubmit}
        onCancel={() => setEditing(false)}
      />
    )
  }

  return (
    <div className="flex min-w-0 flex-1 items-center gap-3">
      <RenameButton
        displayTitle={displayTitle}
        onClick={() => setEditing(true)}
      />
      <Heading className={`${headingClassName} min-w-0 truncate`}>
        {displayTitle}
      </Heading>
    </div>
  )
}
