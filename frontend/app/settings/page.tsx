'use client'

import { GetUserResponse } from '@/lib/client'
import {
  getUserUsersMeGetOptions,
  getUserUsersMeGetQueryKey,
  updateDataRetentionUsersDataRetentionPatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { useGovukModule } from '@/hooks/use-govuk-module'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'

type UserSettingsForm = { dataRetention: 'none' | `${number}` }

export default function SettingsPage() {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  if (!user) {
    return (
      <div className="govuk-width-container govuk-main-wrapper">
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-two-thirds">
            <p className="govuk-body">Loading...</p>
          </div>
        </div>
      </div>
    )
  }
  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <nav className="govuk-breadcrumbs govuk-!-margin-bottom-6" aria-label="Breadcrumb">
        <ol className="govuk-breadcrumbs__list">
          <li className="govuk-breadcrumbs__list-item">
            <Link className="govuk-breadcrumbs__link" href="/">Home</Link>
          </li>
        </ol>
      </nav>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl">Settings</h1>
          <SettingsForm user={user} />
        </div>
      </div>
    </div>
  )
}

function SettingsForm({ user }: { user: GetUserResponse }) {
  const [showSaved, setShowSaved] = useState(false)
  const radiosRef = useRef<HTMLDivElement>(null)
  const savedTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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
            if (savedTimeoutRef.current) {
              clearTimeout(savedTimeoutRef.current)
            }
            setShowSaved(true)
            savedTimeoutRef.current = setTimeout(() => {
              setShowSaved(false)
            }, 3000)
          },
        }
      )
    },
    [mutateAsync, queryClient]
  )
  useEffect(() => {
    const sub = form.watch((_value, { type }) => {
      if (type === 'change') {
        if (savedTimeoutRef.current) clearTimeout(savedTimeoutRef.current)
        setShowSaved(false)
      }
    })
    return () => sub.unsubscribe()
  }, [form])
  useEffect(() => {
    return () => {
      if (savedTimeoutRef.current) {
        clearTimeout(savedTimeoutRef.current)
      }
    }
  }, [])
  return (
    <>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
      >
        <div className="govuk-form-group">
          <fieldset className="govuk-fieldset" aria-describedby="dataRetention-hint">
            <legend className="govuk-fieldset__legend govuk-fieldset__legend--l">
              <h1 className="govuk-fieldset__heading">
                Data Retention Period
              </h1>
            </legend>
            <div id="dataRetention-hint" className="govuk-hint">
              After this period the transcriptions, minutes and audio recording will be permentantly deleted.
            </div>
            <div ref={radiosRef} className="govuk-radios" data-module="govuk-radios">
              <div className="govuk-radios__item">
                <input className="govuk-radios__input" id="keep-indefinitely" type="radio" value="none" {...form.register('dataRetention')} />
                <label className="govuk-label govuk-radios__label" htmlFor="keep-indefinitely">
                  Keep indefinitely
                </label>
              </div>
              <div className="govuk-radios__item">
                <input className="govuk-radios__input" id="one-day" type="radio" value="1" {...form.register('dataRetention')} />
                <label className="govuk-label govuk-radios__label" htmlFor="one-day">
                  1 day
                </label>
              </div>
              <div className="govuk-radios__item">
                <input className="govuk-radios__input" id="seven-days" type="radio" value="7" {...form.register('dataRetention')} />
                <label className="govuk-label govuk-radios__label" htmlFor="seven-days">
                  7 days
                </label>
              </div>
              <div className="govuk-radios__item">
                <input className="govuk-radios__input" id="thirty-days" type="radio" value="30" {...form.register('dataRetention')} />
                <label className="govuk-label govuk-radios__label" htmlFor="thirty-days">
                  30 days
                </label>
              </div>
              <div className="govuk-radios__item">
                <input className="govuk-radios__input" id="ninety-days" type="radio" value="90" {...form.register('dataRetention')} />
                <label className="govuk-label govuk-radios__label" htmlFor="ninety-days">
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
          {isPending && (
            <strong className="govuk-tag">
              Saving...
            </strong>
          )}
          {showSaved && (
            <strong className="govuk-tag govuk-tag--green">
              Saved
            </strong>
          )}
        </div>
      </form>
    </>

  )
}
