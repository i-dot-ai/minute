'use client'

import { GenerateSummaryDialog } from '@/components/audio/generate-summary-dialog'
import { TranscriptionForm } from '@/components/audio/types'
import {
  listTranscriptionsTranscriptionsGetQueryKey,
  retryTranscriptionTranscriptionsTranscriptionIdRetryPostMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useDefaultTemplate } from '@/hooks/useDefaultTemplate'
import { Template } from '@/types/templates'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import posthog from 'posthog-js'
import { useEffect, useState } from 'react'
import { FormProvider, useForm } from 'react-hook-form'

const GENERAL_TEMPLATE: Template = {
  name: 'General',
  description:
    'Standard meeting summary with key points, decisions, and action items',
  agenda_usage: 'optional',
  id: null,
}

export function RetryTranscriptionDialog({
  transcriptionId,
  agenda,
}: {
  transcriptionId: string
  agenda?: string
}) {
  const [open, setOpen] = useState(false)
  const router = useRouter()
  const queryClient = useQueryClient()
  const defaultTemplate = useDefaultTemplate()
  const form = useForm<TranscriptionForm>({
    defaultValues: {
      file: null,
      language: 'en',
      template: GENERAL_TEMPLATE,
      agenda,
    },
  })
  useEffect(() => {
    if (open) {
      form.reset({
        file: null,
        language: form.getValues('language'),
        template: defaultTemplate ?? GENERAL_TEMPLATE,
        agenda,
      })
    }
  }, [agenda, form, open, defaultTemplate])

  const selectedTemplate = form.watch('template')
  const agendaValue = form.watch('agenda')
  const agendaRequired =
    typeof selectedTemplate !== 'string' &&
    selectedTemplate?.agenda_usage === 'required'

  const {
    mutate: retryTranscription,
    isPending,
    error,
    reset,
  } = useMutation({
    ...retryTranscriptionTranscriptionsTranscriptionIdRetryPostMutation(),
  })

  const onSubmit = ({ template, agenda, language }: TranscriptionForm) => {
    retryTranscription(
      {
        path: { transcription_id: transcriptionId },
        body: {
          template_name: template.name,
          template_id: template.id,
          agenda: template.agenda_usage != 'not_used' ? agenda : undefined,
          language,
        },
      },
      {
        onSuccess(transcription) {
          posthog.capture('transcription_started', {
            file_type: '',
            source: 'retry',
          })
          queryClient.invalidateQueries({
            queryKey: listTranscriptionsTranscriptionsGetQueryKey(),
          })
          setOpen(false)
          router.push(`/new/status/${transcription.id}`)
        },
      }
    )
  }

  return (
    <>
      <button
        type="button"
        className="govuk-button"
        onClick={() => {
          reset()
          setOpen(true)
        }}
      >
        Try again
      </button>
      <FormProvider {...form}>
        <GenerateSummaryDialog
          open={open}
          onOpenChange={setOpen}
          onConfirm={form.handleSubmit(onSubmit)}
          disabled={isPending || (agendaRequired && !agendaValue)}
          errorText={
            error
              ? typeof error.detail === 'string'
                ? error.detail
                : 'Could not restart the transcription. Please try again.'
              : undefined
          }
        />
      </FormProvider>
    </>
  )
}
