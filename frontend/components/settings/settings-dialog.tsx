'use client'

import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { useGovukModule } from '@/hooks/use-govuk-module'
import { GetUserResponse } from '@/lib/client'
import {
  getUserUsersMeGetQueryKey,
  listTranscriptionsTranscriptionsGetQueryKey,
  updateDataRetentionUsersDataRetentionPatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'

type UserSettingsForm = { dataRetention: 'none' | `${number}` }

export function SettingsDialog({ user }: { user: GetUserResponse }) {
  const [open, setOpen] = useState(false)
  const radiosRef = useRef<HTMLDivElement>(null)

  useGovukModule(radiosRef, 'Radios')
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

  useEffect(() => {
    if (open) {
      form.reset({
        dataRetention: user.data_retention_days
          ? `${user.data_retention_days}`
          : 'none',
      })
    }
  }, [form, open, user.data_retention_days])

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
            queryClient.invalidateQueries({
              queryKey: listTranscriptionsTranscriptionsGetQueryKey(),
            })
            setOpen(false)
          },
        }
      )
    },
    [mutateAsync, queryClient]
  )

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button
          type="button"
          className="govuk-link govuk-link--no-visited-state text-(--govuk-link-colour)"
        >
          Change data retention period
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle className="govuk-heading-l">
          Data retention period
        </DialogTitle>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <div className="govuk-form-group">
            <fieldset
              className="govuk-fieldset"
              aria-describedby="dataRetention-hint"
            >
              <div id="dataRetention-hint" className="govuk-hint">
                After this period the transcriptions, minutes and audio
                recording will be permanently deleted.
              </div>
              <div
                ref={radiosRef}
                className="govuk-radios govuk-radios--small"
                data-module="govuk-radios"
              >
                <div className="govuk-radios__item">
                  <input
                    className="govuk-radios__input"
                    id="keep-indefinitely"
                    type="radio"
                    value="none"
                    {...form.register('dataRetention')}
                  />
                  <label
                    className="govuk-label govuk-radios__label"
                    htmlFor="keep-indefinitely"
                  >
                    Keep indefinitely
                  </label>
                </div>
                <div className="govuk-radios__item">
                  <input
                    className="govuk-radios__input"
                    id="one-day"
                    type="radio"
                    value="1"
                    {...form.register('dataRetention')}
                  />
                  <label
                    className="govuk-label govuk-radios__label"
                    htmlFor="one-day"
                  >
                    1 day
                  </label>
                </div>
                <div className="govuk-radios__item">
                  <input
                    className="govuk-radios__input"
                    id="seven-days"
                    type="radio"
                    value="7"
                    {...form.register('dataRetention')}
                  />
                  <label
                    className="govuk-label govuk-radios__label"
                    htmlFor="seven-days"
                  >
                    7 days
                  </label>
                </div>
                <div className="govuk-radios__item">
                  <input
                    className="govuk-radios__input"
                    id="thirty-days"
                    type="radio"
                    value="30"
                    {...form.register('dataRetention')}
                  />
                  <label
                    className="govuk-label govuk-radios__label"
                    htmlFor="thirty-days"
                  >
                    30 days
                  </label>
                </div>
                <div className="govuk-radios__item">
                  <input
                    className="govuk-radios__input"
                    id="ninety-days"
                    type="radio"
                    value="90"
                    {...form.register('dataRetention')}
                  />
                  <label
                    className="govuk-label govuk-radios__label"
                    htmlFor="ninety-days"
                  >
                    90 days
                  </label>
                </div>
              </div>
            </fieldset>
          </div>
          <div className="govuk-button-group">
            <button
              type="submit"
              className="govuk-button"
              data-module="govuk-button"
              disabled={isPending}
            >
              Save
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
