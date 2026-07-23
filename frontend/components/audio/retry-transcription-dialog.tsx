'use client'

import { GenerateSummaryDialog } from '@/components/audio/generate-summary-dialog'
import { TranscriptionForm } from '@/components/audio/types'
import { createTranscriptionTranscriptionsPostMutation } from '@/lib/client/@tanstack/react-query.gen'
import { useDefaultTemplate } from '@/hooks/useDefaultTemplate'
import { Template } from '@/types/templates'
import { useMutation } from '@tanstack/react-query'
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
  recordingId,
  agenda,
  title,
}: {
  recordingId: string
  agenda?: string
  title?: string
}) {
  const [open, setOpen] = useState(false)
  const router = useRouter()
  const defaultTemplate = useDefaultTemplate()
  const form = useForm<TranscriptionForm>({
    defaultValues: {
      file: null,
      template: GENERAL_TEMPLATE,
      agenda,
    },
  })
  useEffect(() => {
    if (open) {
      form.reset({
        file: null,
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

  const { mutate: createTranscription, isPending } = useMutation({
    ...createTranscriptionTranscriptionsPostMutation(),
  })

  const onSubmit = ({ template, agenda }: TranscriptionForm) => {
    createTranscription(
      {
        body: {
          recording_id: recordingId,
          template_name: template.name,
          template_id: template.id,
          agenda: template.agenda_usage != 'not_used' ? agenda : undefined,
          title,
        },
      },
      {
        onSuccess(transcription) {
          posthog.capture('transcription_started', {
            file_type: '',
            source: 'retry',
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
        onClick={() => setOpen(true)}
      >
        Try again
      </button>
      <FormProvider {...form}>
        <GenerateSummaryDialog
          open={open}
          onOpenChange={setOpen}
          onConfirm={form.handleSubmit(onSubmit)}
          disabled={isPending || (agendaRequired && !agendaValue)}
        />
      </FormProvider>
    </>
  )
}
