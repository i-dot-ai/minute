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

export function NewMinuteDialog({
  transcriptionId,
  agenda,
  disabled,
}: {
  transcriptionId: string
  agenda?: string
  disabled?: boolean
}) {
  const [open, setOpen] = useState(false)
  const form = useForm<CreateMinuteForm>({
    defaultValues: {
      template: { name: 'General', agenda_usage: 'optional', id: null },
      agenda,
    },
  })
  useEffect(() => {
    if (open) {
      form.reset({
        template: { name: 'General', agenda_usage: 'optional', id: null },
        agenda,
      })
    }
  }, [agenda, form, open])
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
        onSuccess() {
          queryClient.invalidateQueries({
            queryKey:
              listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetQueryKey(
                { path: { transcription_id: transcriptionId } }
              ),
          })
          posthog.capture('generate_ai_minutes_started', {
            style: !!template.id ? 'User generated' : template.name,
          })
          setOpen(false)
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
        <button className="govuk-button govuk-button--secondary" disabled={disabled}>
          <Plus className="size-4" />
          Generate new summary
        </button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-auto lg:min-w-3xl">
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
                  <label className="govuk-label govuk-label--m" htmlFor="agenda">
                    Agenda (
                    {selectedTemplate.agenda_usage == 'optional'
                      ? 'optional'
                      : 'required'}
                    ):
                  </label>
                </h3>
                <div id="agenda-hint" className="govuk-hint">
                  Add discussion points from the meeting that should be included in
                  the summary.
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
