'use client'

import { TemplateSelect } from '@/components/template-select/template-select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  createMinuteTranscriptionTranscriptionIdMinutesPostMutation,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useDefaultTemplate } from '@/hooks/useDefaultTemplate'
import { Template } from '@/types/templates'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import posthog from 'posthog-js'
import { useEffect, useState } from 'react'
import { useController, useForm } from 'react-hook-form'

type CreateMinuteForm = {
  template: Template
  agenda?: string
}

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
  const form = useForm<CreateMinuteForm>({
    defaultValues: {
      template: GENERAL_TEMPLATE,
      agenda,
    },
  })
  useEffect(() => {
    if (open) {
      form.reset({
        template: defaultTemplate ?? GENERAL_TEMPLATE,
        agenda,
      })
    }
  }, [agenda, form, open, defaultTemplate])
  const queryClient = useQueryClient()

  const selectedTemplate = form.watch('template')

  const { mutate: createMinute } = useMutation({
    ...createMinuteTranscriptionTranscriptionIdMinutesPostMutation(),
  })

  const onSubmit = ({ template, agenda }: CreateMinuteForm) => {
    createMinute(
      {
        path: { transcription_id: transcriptionId },
        body: {
          template_name: template.name,
          template_id: template.id,
          agenda:
            selectedTemplate.agenda_usage != 'not_used' ? agenda : undefined,
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

  const { field } = useController({
    control: form.control,
    name: 'template',
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button
          className="govuk-button govuk-button--secondary flex items-center gap-2"
          disabled={disabled}
        >
          <Plus className="size-4" />
          New summary
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="govuk-heading-l">
            Generate a new summary
          </DialogTitle>
          <DialogDescription className="govuk-body">
            Choose a template style for your meeting summary
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <TemplateSelect value={field.value} onChange={field.onChange} />
          {selectedTemplate && selectedTemplate.agenda_usage != 'not_used' && (
            <div>
              <div className="govuk-form-group">
                <h3 className="govuk-label-wrapper">
                  <label
                    className="govuk-label govuk-label--m"
                    htmlFor="agenda"
                  >
                    Agenda (
                    {selectedTemplate.agenda_usage == 'optional'
                      ? 'optional'
                      : 'required'}
                    ):
                  </label>
                </h3>
                <div id="agenda-hint" className="govuk-hint">
                  Add discussion points from the meeting that should be included
                  in the summary.
                </div>
                <textarea
                  className="govuk-textarea"
                  id="agenda"
                  rows={5}
                  aria-describedby="agenda-hint"
                  {...form.register('agenda', {
                    required: selectedTemplate.agenda_usage == 'required',
                  })}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <button
              className="govuk-button govuk-button--secondary"
              type="button"
              onClick={() => setOpen(false)}
            >
              Cancel
            </button>
            <button
              className="govuk-button"
              type="submit"
              disabled={
                !selectedTemplate ||
                (selectedTemplate.agenda_usage == 'required' &&
                  !form.watch('agenda'))
              }
            >
              Generate minute
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
