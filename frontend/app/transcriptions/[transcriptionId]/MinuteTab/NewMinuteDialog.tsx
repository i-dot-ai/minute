'use client'

import { GenerateSummaryDialog } from '@/components/audio/generate-summary-dialog'
import { TranscriptionForm } from '@/components/audio/types'
import {
  createMinuteTranscriptionTranscriptionIdMinutesPostMutation,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useDefaultTemplate } from '@/hooks/useDefaultTemplate'
import { Template } from '@/types/templates'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import posthog from 'posthog-js'
import { useEffect, useState } from 'react'
import { FormProvider, useForm } from 'react-hook-form'
import { PlusIcon } from 'lucide-react'

const GENERAL_TEMPLATE: Template = {
  name: 'General',
  description:
    'Standard meeting summary with key points, decisions, and action items',
  agenda_usage: 'optional',
  id: null,
}

export function NewMinuteDialog({
  transcriptionId,
  agenda,
  disabled,
  onCreated,
}: {
  transcriptionId: string
  agenda?: string
  disabled?: boolean
  onCreated?: () => void
}) {
  const [open, setOpen] = useState(false)
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
  const queryClient = useQueryClient()

  const selectedTemplate = form.watch('template')
  const agendaValue = form.watch('agenda')
  const agendaRequired =
    typeof selectedTemplate !== 'string' &&
    selectedTemplate?.agenda_usage === 'required'

  const { mutate: createMinute, isPending } = useMutation({
    ...createMinuteTranscriptionTranscriptionIdMinutesPostMutation(),
  })

  const onSubmit = ({ template, agenda }: TranscriptionForm) => {
    createMinute(
      {
        path: { transcription_id: transcriptionId },
        body: {
          template_name: template.name,
          template_id: template.id,
          agenda: template.agenda_usage != 'not_used' ? agenda : undefined,
        },
      },
      {
        async onSuccess() {
          await queryClient.invalidateQueries({
            queryKey:
              listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetQueryKey(
                { path: { transcription_id: transcriptionId } }
              ),
          })
          posthog.capture('generate_ai_minutes_started', {
            style: !!template.id ? 'User generated' : template.name,
          })
          setOpen(false)
          onCreated?.()
        },
      }
    )
  }

  return (
    <>
      <button
        type="button"
        className="govuk-button govuk-button--secondary !w-full"
        disabled={disabled}
        onClick={() => setOpen(true)}
      >
        <PlusIcon className="size-4" /> New summary
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
