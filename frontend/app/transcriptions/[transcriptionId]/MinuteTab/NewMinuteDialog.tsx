'use client'

import { TemplateSelect } from '@/components/template-radio-group'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import {
  createMinuteTranscriptionTranscriptionIdMinutesPostMutation,
  getTemplatesTemplatesGetOptions,
  listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import posthog from 'posthog-js'
import { useEffect, useMemo, useState } from 'react'
import { useController, useForm } from 'react-hook-form'

type CreateMinuteForm = {
  templateName: string
  agenda?: string
}

export function NewMinuteDialog({
  transcriptionId,
  agenda,
}: {
  transcriptionId: string
  agenda?: string
}) {
  const [open, setOpen] = useState(false)
  const form = useForm<CreateMinuteForm>({
    defaultValues: { templateName: 'General', agenda },
  })
  useEffect(() => {
    if (open) {
      form.reset({ templateName: 'General', agenda })
    }
  }, [agenda, form, open])
  const queryClient = useQueryClient()

  // Fetch templates from API
  const { data: templates = [], isLoading: isLoadingTemplates } = useQuery(
    getTemplatesTemplatesGetOptions()
  )
  const templateName = form.watch('templateName')
  const selectedTemplate = useMemo(
    () =>
      templates.length
        ? templates.find((t) => t.name == templateName)
        : undefined,
    [templateName, templates]
  )

  const { mutate: createMinute } = useMutation({
    ...createMinuteTranscriptionTranscriptionIdMinutesPostMutation(),
  })

  const onSubmit = ({ templateName, agenda }: CreateMinuteForm) => {
    if (!templateName) {
      return
    }
    createMinute(
      {
        path: { transcription_id: transcriptionId },
        body: {
          template_name: templateName,
          agenda:
            selectedTemplate?.agenda_usage != 'not_used' ? agenda : undefined,
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
            style: templateName,
          })
          setOpen(false)
        },
      }
    )
  }

  const { field } = useController({
    control: form.control,
    name: 'templateName',
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="flex gap-2 bg-blue-600 hover:bg-blue-800">
          <Plus /> Generate New
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-auto lg:min-w-3xl">
        <DialogHeader>
          <DialogTitle className="text-3xl font-bold">
            Generate a new minute
          </DialogTitle>
          <DialogDescription className="text-muted-foreground mt-1 mb-4 text-sm">
            Choose a template style for your meeting summary
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <TemplateSelect
            value={field.value}
            onChange={field.onChange}
            templates={templates}
            isLoading={isLoadingTemplates}
          />
          {selectedTemplate && selectedTemplate.agenda_usage != 'not_used' && (
            <div className="mb-4 rounded">
              <h3 className="text-semibold m">
                Agenda (
                {selectedTemplate.agenda_usage == 'optional'
                  ? 'optional'
                  : 'required'}
                ):
              </h3>
              <p className="text-muted-foreground text-sm">
                Add discussion points from the meeting that should be included
                in the summary.
              </p>
              <Textarea
                className="bg-white"
                placeholder={`Agenda item 1
Agenda item 2
Agenda item 3
...`}
                {...form.register('agenda', {
                  required: selectedTemplate.agenda_usage == 'required',
                })}
              />
            </div>
          )}
          <DialogFooter>
            <Button
              variant="secondary"
              type="button"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="bg-blue-500 hover:bg-blue-800 active:bg-yellow-400"
              disabled={
                isLoadingTemplates ||
                !selectedTemplate ||
                (selectedTemplate.agenda_usage == 'required' &&
                  !form.watch('agenda'))
              }
            >
              Generate minute
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
