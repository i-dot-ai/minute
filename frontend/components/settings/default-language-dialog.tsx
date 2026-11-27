'use client'

import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { GetUserResponse } from '@/lib/client'
import {
  getUserUsersMeGetQueryKey,
  updateDefaultLanguageUsersDefaultLanguagePatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

export function DefaultLanguageDialog({ user }: { user: GetUserResponse }) {
  const [open, setOpen] = useState(false)
  const [language, setLanguage] = useState<'english' | 'cymraeg'>(
    user.default_language ?? 'english'
  )
  const queryClient = useQueryClient()
  const { mutateAsync, isPending } = useMutation({
    ...updateDefaultLanguageUsersDefaultLanguagePatchMutation(),
  })

  const onOpenChange = (open: boolean) => {
    if (open) {
      // Reset any unsaved pick from a previous open.
      setLanguage(user.default_language ?? 'english')
    }
    setOpen(open)
  }

  const save = async () => {
    await mutateAsync(
      { body: { default_language: language } },
      {
        onSuccess() {
          queryClient.invalidateQueries({
            queryKey: getUserUsersMeGetQueryKey(),
          })
          setOpen(false)
        },
      }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <button
          type="button"
          className="govuk-link govuk-link--no-visited-state govuk-link--no-underline text-(--govuk-link-colour)"
        >
          Change default language
        </button>
      </DialogTrigger>
      <DialogContent>
        <div className="govuk-form-group">
          <fieldset
            className="govuk-fieldset"
            aria-describedby="change-language-hint"
          >
            <legend className="govuk-fieldset__legend">
              <DialogTitle className="govuk-heading-l">
                Choose default language
              </DialogTitle>
            </legend>
            <div className="govuk-hint" id="change-language-hint">
              You can change this for each individual recording when you start a
              new one
            </div>
            <div
              className="govuk-radios govuk-radios--small"
              data-module="govuk-radios"
            >
              <div className="govuk-radios__item">
                <input
                  className="govuk-radios__input"
                  id="default-language-english"
                  name="default-language"
                  type="radio"
                  value="english"
                  checked={language === 'english'}
                  onChange={() => setLanguage('english')}
                />
                <label
                  className="govuk-label govuk-radios__label"
                  htmlFor="default-language-english"
                >
                  English
                </label>
              </div>
              <div className="govuk-radios__item">
                <input
                  className="govuk-radios__input"
                  id="default-language-cymraeg"
                  name="default-language"
                  type="radio"
                  value="cymraeg"
                  checked={language === 'cymraeg'}
                  onChange={() => setLanguage('cymraeg')}
                />
                <label
                  className="govuk-label govuk-radios__label"
                  htmlFor="default-language-cymraeg"
                >
                  Cymraeg
                </label>
              </div>
            </div>
          </fieldset>
        </div>
        <div className="govuk-button-group">
          <button
            type="button"
            className="govuk-button"
            data-module="govuk-button"
            disabled={isPending}
            onClick={save}
          >
            Save
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
