'use client'

import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Textarea } from '@/components/ui/textarea'
import { createMinuteVersionMinutesMinuteIdVersionsPostMutation } from '@/lib/client/@tanstack/react-query.gen'
import { useMutation } from '@tanstack/react-query'
import { Wand2Icon } from 'lucide-react'
import { useCallback, useState } from 'react'
import { useForm } from 'react-hook-form'

type AIEditFormData = { instruction: string }

export const AiEditPopover = ({
  disabled,
  minuteId,
  minuteVersionId,
  onSuccess,
}: {
  disabled: boolean
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
          { onSuccess }
        )
      }
    },
    [minuteId, minuteVersionId, onSuccess, saveEdit]
  )
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <Button
        className="bg-indigo-700 hover:bg-indigo-800 active:bg-yellow-500"
        type="button"
        disabled={disabled}
        asChild
      >
        <PopoverTrigger>
          <Wand2Icon />
          AI Edit
        </PopoverTrigger>
      </Button>
      <PopoverContent className="w-xl max-w-screen">
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <Textarea
            placeholder="Describe the changes you want to make (you can always revert the changes if you don't like them)."
            {...form.register('instruction')}
          />
          <Button
            className="mt-2 bg-indigo-700 hover:bg-indigo-800 active:bg-yellow-500"
            type="submit"
            disabled={!form.watch('instruction')}
          >
            <Wand2Icon /> Apply AI Edit
          </Button>
        </form>
      </PopoverContent>
    </Popover>
  )
}
