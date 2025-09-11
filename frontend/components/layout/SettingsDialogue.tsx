'use client'

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
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { GetUserResponse } from '@/lib/client'
import {
  getUserUsersMeGetOptions,
  getUserUsersMeGetQueryKey,
  updateDataRetentionUsersDataRetentionPatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader, Settings } from 'lucide-react'
import { useCallback, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'

type UserSettingsForm = { dataRetention: 'none' | `${number}` }

export const SettingsDialogue = () => {
  const [open, setOpen] = useState(false)
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  return (
    <>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button variant="ghost">
            <Settings />
          </Button>
        </DialogTrigger>
        {user && <SettingsDialogueForm user={user} />}
      </Dialog>
    </>
  )
}

function SettingsDialogueForm({ user }: { user: GetUserResponse }) {
  const queryClient = useQueryClient()
  const { mutateAsync, isPending } = useMutation({
    ...updateDataRetentionUsersDataRetentionPatchMutation(),
  })
  const form = useForm<UserSettingsForm>({
    defaultValues: {
      dataRetention: user.data_retention_days
        ? `${user.data_retention_days}`
        : 'none',
    },
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
    <DialogContent className="sm:max-w-[425px]">
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>
            {user.strict_data_retention
              ? "Due to your organisation's retention policy you cannot adjust your data retention preferences. Transcripts and summaries will be kept for 24 hours."
              : 'Configure your data retention preferences.'}
          </DialogDescription>
        </DialogHeader>
        <div>
          <Label htmlFor="dataRetention" className="mt-4 mb-2">
            Data Retention Period
          </Label>
          <Controller
            disabled={user.strict_data_retention}
            control={form.control}
            name="dataRetention"
            render={({ field: { onChange, value, ref, disabled } }) => (
              <Select
                value={user.strict_data_retention ? '1' : value}
                onValueChange={onChange}
                disabled={disabled}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Data retention period" ref={ref} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Keep indefinitely</SelectItem>
                  <SelectItem value="1">1 day</SelectItem>
                  <SelectItem value="7">7 days</SelectItem>
                  <SelectItem value="30">30 days</SelectItem>
                  <SelectItem value="90">90 days</SelectItem>
                </SelectContent>
              </Select>
            )}
          />
        </div>
        <DialogFooter>
          <Button
            disabled={user.strict_data_retention}
            type="submit"
            className="hover:bg-blue-800 active:bg-yellow-400"
          >
            {isPending ? <Loader /> : 'Save'}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  )
}
