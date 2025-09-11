'use client'

import { Rating } from '@/app/transcriptions/[transcriptionId]/MinuteTab/components/rating-dialog/rating'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { DialogueEntry } from '@/lib/client'
import posthog from 'posthog-js'
import { useCallback, useEffect, useState } from 'react'
import { Controller, FormProvider, useForm } from 'react-hook-form'

export const RatingButton = ({
  minuteVersionId,
  transcript,
  minutes,
}: {
  minuteVersionId: string
  transcript: DialogueEntry[] | null
  minutes: string | null
}) => {
  const [rating, setRating] = useState<number | null>(null)
  const [isOpen, onOpenChange] = useState(false)
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogTrigger asChild type="button">
        <div className="flex items-center gap-2 text-gray-600 transition-colors hover:text-gray-900">
          <span className="text-sm">Rate summary</span>
          <div className="flex items-center gap-1">
            <Rating className="size-4" value={rating} onChange={setRating} />
          </div>
        </div>
      </DialogTrigger>
      <RatingForm
        initialValue={rating}
        minuteVersionId={minuteVersionId}
        minutes={minutes}
        transcript={transcript}
        close={() => onOpenChange(false)}
      />
    </Dialog>
  )
}

type RatingFormData = {
  rating: number | null
  shareContent: boolean
  comment: string
}

const RatingForm = ({
  initialValue,
  minuteVersionId,
  transcript,
  minutes,
  close,
}: {
  initialValue: number | null
  minuteVersionId: string
  transcript: DialogueEntry[] | null
  minutes: string | null
  close: () => void
}) => {
  const form = useForm<RatingFormData>()
  useEffect(() => {
    form.setValue('rating', initialValue)
  }, [form, initialValue])
  const rating = form.watch('rating')
  const onSubmit = useCallback(
    ({ rating, comment, shareContent }: RatingFormData) => {
      if (rating) {
        posthog.capture('minutes_rating_submitted', {
          rating,
          comment,
          version_id: minuteVersionId,
          ...(shareContent && {
            minutes_content: minutes,
            transcript,
          }),
        })
      }
      close()
    },
    [close, minuteVersionId, minutes, transcript]
  )
  return (
    <DialogContent className="sm:max-w-[425px]">
      <FormProvider {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle className="text-center text-xl font-semibold">
              How did we do?
            </DialogTitle>
            <DialogDescription className="text-center text-gray-600">
              Your feedback helps us improve our AI summaries. We read every
              single response! 🙏
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-6 py-4">
            <div className="flex flex-col items-center gap-3">
              <Controller
                control={form.control}
                name="rating"
                render={({ field: { value, onChange } }) => (
                  <Rating
                    className="size-7"
                    value={value}
                    onChange={onChange}
                  />
                )}
              />
              <span className="text-sm text-gray-500">
                {rating
                  ? `${rating} star${rating !== 1 ? 's' : ''}`
                  : 'Select a rating'}
              </span>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Any specific feedback? (Optional)
              </label>
              <Textarea
                placeholder="Tell us what worked well or what we could improve..."
                {...form.register('comment')}
                className="min-h-[100px] resize-none"
              />
            </div>
            <div className="flex items-start gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3">
              <input
                type="checkbox"
                {...form.register('shareContent')}
                className="mt-1 size-4 rounded border-gray-300"
              />
              <div className="space-y-1">
                <label
                  htmlFor="shareContent"
                  className="text-sm font-medium text-gray-700"
                >
                  Share the summary & transcript with us?
                </label>
                <p className="text-xs text-gray-500">
                  You can optionally share the summary and transcript with us
                  which will help us directly improve Minute. Your content is
                  not used for model training.
                </p>
              </div>
            </div>
            <Button
              type="submit"
              className="w-full bg-indigo-600 text-white transition-all hover:bg-indigo-700 disabled:opacity-50"
              disabled={!rating}
            >
              {rating ? 'Submit Feedback' : 'Select a Rating'}
            </Button>
            <p className="text-center text-xs text-gray-500">
              Thanks for helping us make our AI summaries better!
            </p>
          </div>
        </form>
      </FormProvider>
    </DialogContent>
  )
}
