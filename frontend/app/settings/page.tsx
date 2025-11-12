'use client'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { GetUserResponse } from '@/lib/client'
import {
  getUserUsersMeGetOptions,
  getUserUsersMeGetQueryKey,
  updateDataRetentionUsersDataRetentionPatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, Loader, Loader2, TriangleAlert } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useCallback } from 'react'
import { Controller, useForm } from 'react-hook-form'

type UserSettingsForm = { dataRetention: 'none' | `${number}` }

export default function SettingsPage() {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  const router = useRouter()
  if (!user) {
    return (
      <div className="mx-auto flex max-w-3xl items-center gap-2 pt-1">
        <Loader2 className="animate-spin" />
        Loading...
      </div>
    )
  }
  return (
    <div className="mx-auto max-w-3xl pt-1">
      <Button
        variant="link"
        className="mb-4 self-start px-0! underline hover:decoration-2"
        onClick={() => {
          router.back()
        }}
      >
        <span className="flex items-center">
          <ChevronLeft />
          Back
        </span>
      </Button>
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <div className="text-muted-foreground">
          Configure your account settings
        </div>
      </div>
      <SettingsForm user={user} />
    </div>
  )
}

function SettingsForm({ user }: { user: GetUserResponse }) {
  const form = useForm<UserSettingsForm>({
    defaultValues: {
      dataRetention: user.data_retention_days
        ? `${user.data_retention_days}`
        : 'none',
    },
  })
  const queryClient = useQueryClient()
  const { mutateAsync, isPending } = useMutation({
    ...updateDataRetentionUsersDataRetentionPatchMutation(),
  })

  const onSubmit = useCallback(
    async (data: UserSettingsForm) => {
      await mutateAsync(
        {
          body: {
            data_retention_days:
              data.dataRetention === 'none' ? null : Number(data.dataRetention),
          },
        },
        {
          onSuccess() {
            queryClient.invalidateQueries({
              queryKey: getUserUsersMeGetQueryKey(),
            })
          },
        }
      )
    },
    [mutateAsync, queryClient]
  )
  return (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      className="mt-4 flex flex-col gap-6"
    >
      <div className="mt-2">
        <Label htmlFor="dataRetention">Data Retention Period</Label>
        <p className="text-muted-foreground mt-1 mb-2 text-sm">
          After this period the transcriptions, minutes and audio recording will
          be permentantly deleted.
        </p>
        {user.strict_data_retention && (
          <Alert className="my-2">
            <TriangleAlert />
            <AlertTitle>Your retention period cannot be changed.</AlertTitle>
            <AlertDescription>
              Due to your organisation&apos;s retention policy you cannot adjust
              your data retention preferences. Transcripts and summaries will be
              kept for 24 hours.
            </AlertDescription>
          </Alert>
        )}
        <Controller
          disabled={user.strict_data_retention}
          control={form.control}
          name="dataRetention"
          render={({ field: { onChange, value, ref, disabled } }) => (
            <RadioGroup
              value={user.strict_data_retention ? '1' : value}
              onValueChange={onChange}
              disabled={disabled}
              ref={ref}
            >
              <Label>
                <RadioGroupItem value="none" />
                Keep indefinitely
              </Label>
              <Label>
                <RadioGroupItem value="1" /> 1 day
              </Label>
              <Label>
                <RadioGroupItem value="7" /> 7 days
              </Label>
              <Label>
                <RadioGroupItem value="30" /> 30 days
              </Label>
              <Label>
                <RadioGroupItem value="90" /> 90 days
              </Label>
            </RadioGroup>
          )}
        />
      </div>
      <div>
        <Button
          disabled={user.strict_data_retention}
          type="submit"
          className="hover:bg-blue-800 active:bg-yellow-400"
        >
          {isPending ? <Loader /> : 'Save'}
        </Button>
      </div>
    </form>
  )
}
