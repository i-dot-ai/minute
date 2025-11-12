import { Button } from '@/components/ui/button'
import {
  getTranscriptionTranscriptionsTranscriptionIdGetQueryKey,
  saveTranscriptionTranscriptionsTranscriptionIdPatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { cn } from '@/lib/utils'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Edit } from 'lucide-react'
import posthog from 'posthog-js'
import { useCallback, useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'

export const TranscriptionTitleEditor = ({
  transcriptionId,
  title,
}: {
  transcriptionId: string
  title: string | null
}) => {
  const [editing, setEditing] = useState(false)
  const queryClient = useQueryClient()
  const form = useForm<{ title: string }>({
    defaultValues: { title: title || '' },
    mode: 'onBlur',
  })
  const { mutate: saveTranscription } = useMutation({
    ...saveTranscriptionTranscriptionsTranscriptionIdPatchMutation(),
  })
  const onSubmit = useCallback(
    ({ title }: { title: string }) => {
      saveTranscription(
        {
          path: { transcription_id: transcriptionId },
          body: { title },
        },
        {
          onSuccess() {
            queryClient.invalidateQueries({
              queryKey:
                getTranscriptionTranscriptionsTranscriptionIdGetQueryKey({
                  path: { transcription_id: transcriptionId },
                }),
            })
            posthog.capture('edited_transcript_title', {
              transcriptionId: transcriptionId,
            })
            setEditing(false)
          },
        }
      )
    },
    [queryClient, saveTranscription, transcriptionId]
  )
  useEffect(() => {
    if (editing) {
      form.setFocus('title', { shouldSelect: true })
    }
  }, [editing, form])

  if (editing) {
    return (
      <input
        {...form.register('title', {
          onBlur: () => {
            form.handleSubmit(onSubmit)()
            setEditing(false)
          },
        })}
        className="rounded-md border-2 border-slate-400 text-3xl font-bold"
        placeholder="Add title"
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            form.handleSubmit(onSubmit)()
            setEditing(false)
          }
        }}
      />
    )
  }

  return (
    <div className="flex items-baseline gap-2">
      <h1 className={cn('text-3xl font-bold', { 'text-gray-400': !title })}>
        {form.watch('title') || 'Add title'}
      </h1>
      <Button
        onClick={() => {
          setEditing(true)
        }}
        variant="ghost"
        className="text-slate-500"
      >
        <Edit /> Rename
      </Button>
    </div>
  )
}
