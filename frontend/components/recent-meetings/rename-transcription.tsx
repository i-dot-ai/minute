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
import { ReactNode, useCallback, useEffect, useRef, useState } from 'react'
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

function useRenameTranscription(transcription: RenameTranscription) {
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

export type RenameTranscriptionParts = {
  button: ReactNode
  title: ReactNode
  form: ReactNode
  editing: boolean
}

export function RenameTranscriptionInline({
  transcription,
  headingLevel = 'h2',
  headingClassName = 'govuk-body govuk-!-margin-bottom-0',
  children,
}: {
  transcription: RenameTranscription
  headingLevel?: 'h1' | 'h2' | 'h3'
  headingClassName?: string
  children?: (parts: RenameTranscriptionParts) => ReactNode
}) {
  const [editing, setEditing] = useState(false)
  const skipBlurSaveRef = useRef(false)
  const { save, isPending } = useRenameTranscription(transcription)
  const displayTitle = getTranscriptionDisplayTitle(
    transcription.title,
    transcription.status
  )
  const inputId = `transcription-title-${transcription.id}`
  const hintId = `${inputId}-hint`
  const statusId = `${inputId}-status`

  const form = useForm<{ title: string }>({
    defaultValues: { title: transcription.title ?? '' },
  })

  const cancel = useCallback(() => {
    form.reset({ title: transcription.title ?? '' })
    setEditing(false)
  }, [form, transcription.title])

  const onSubmit = useCallback(
    ({ title }: { title: string }) => {
      skipBlurSaveRef.current = true
      save(title)
      setEditing(false)
    },
    [save]
  )

  useEffect(() => {
    if (editing) {
      skipBlurSaveRef.current = false
      form.reset({ title: transcription.title ?? '' })
      form.setFocus('title', { shouldSelect: true })
    }
  }, [editing, form, transcription.title])

  const Heading = headingLevel

  const button = (
    <button
      type="button"
      data-module="govuk-button"
      className="govuk-link shrink-0 text-(--govuk-link-colour) govuk-!-margin-bottom-0 hover:cursor-pointer"
      onClick={() => setEditing(true)}
      aria-label={`Rename ${displayTitle}`}
    >
      <PencilIcon className="size-4" aria-hidden="true" />
      <span className="govuk-visually-hidden">Rename {displayTitle}</span>
    </button>
  )

  const title = (
    <Heading className={`${headingClassName} min-w-0 truncate`}>
      {displayTitle}
    </Heading>
  )

  const formElement = (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
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
            form.handleSubmit(onSubmit)()
          }
          if (e.key === 'Escape') {
            e.preventDefault()
            skipBlurSaveRef.current = true
            cancel()
          }
        }}
        {...form.register('title', {
          onBlur: () => {
            if (skipBlurSaveRef.current) {
              skipBlurSaveRef.current = false
              return
            }
            form.handleSubmit(onSubmit)()
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

  const parts: RenameTranscriptionParts = {
    button,
    title,
    form: formElement,
    editing,
  }

  if (children) {
    return children(parts)
  }

  if (editing) {
    return formElement
  }

  return (
    <div className="flex min-w-0 flex-1 items-center gap-3">
      {button}
      {title}
    </div>
  )
}
