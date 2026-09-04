'use client'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { createMinuteVersionMinutesMinuteIdVersionsPostMutation } from '@/lib/client/@tanstack/react-query.gen'
import { useMutation } from '@tanstack/react-query'
import { Wand2Icon } from 'lucide-react'
import { useCallback, useState } from 'react'
import { useForm } from 'react-hook-form'

type AIEditFormData = { instruction: string }

export const AiEditPopover = ({
  minuteId,
  minuteVersionId,
  onSuccess,
}: {
  minuteId: string
  minuteVersionId: string
  onSuccess: () => void
}) => {
  const [open, setOpen] = useState(false)
  const form = useForm<AIEditFormData>()
  const { mutate: saveEdit } = useMutation({
    ...createMinuteVersionMinutesMinuteIdVersionsPostMutation(),
  })
  const onSubmit = useCallback(
    ({ instruction }: AIEditFormData) => {
      if (instruction) {
        saveEdit(
          {
            path: { minute_id: minuteId },
            body: {
              content_source: 'ai_edit',
              ai_edit_instructions: { instruction, source_id: minuteVersionId },
            },
          },
          {
            onSuccess: () => {
              setOpen(false)
              form.reset()
              onSuccess()
            },
          }
        )
      }
    },
    [form, minuteId, minuteVersionId, onSuccess, saveEdit]
  )
  return (
    <Dialog
      open={open}
      onOpenChange={(isOpen) => {
        setOpen(isOpen)
        if (!isOpen) {
          form.reset()
        }
      }}
    >
      <DialogTrigger asChild>
        <button
          className="govuk-button govuk-button--secondary sm:mb-0"
          type="button"
        >
          <Wand2Icon className="size-4" /> AI edit
        </button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-auto lg:min-w-xl">
        <DialogTitle className="govuk-heading-l">AI edit</DialogTitle>
        <DialogDescription className="govuk-body">
          Describe the changes you want to make. You can always revert if you
          don&apos;t like them.
        </DialogDescription>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <div className="govuk-form-group">
            <label className="govuk-label" htmlFor="ai-edit-instruction">
              Edit instruction
            </label>
            <textarea
              className="govuk-textarea"
              id="ai-edit-instruction"
              rows={5}
              placeholder="e.g. Make the tone more formal and shorten the eligibility section"
              {...form.register('instruction')}
            />
          </div>
          <div className="govuk-button-group justify-end">
            <button
              type="button"
              className="govuk-button govuk-button--secondary"
              onClick={() => setOpen(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="govuk-button"
              disabled={!form.watch('instruction')}
            >
              Apply AI edit
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
