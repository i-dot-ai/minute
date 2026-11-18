'use client'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  getUserUsersMeGetQueryKey,
  updateDisplayNameUsersDisplayNamePatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { FormEvent, useEffect, useState } from 'react'

export const ChangeNameDialog = ({
  open,
  onOpenChange,
  displayName,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  displayName?: string
}) => {
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  // Seed from the current name every time the dialog opens
  useEffect(() => {
    if (open) {
      setName(displayName ?? '')
      setError(null)
    }
  }, [open, displayName])

  const { mutate: patchDisplayName, isPending } = useMutation({
    ...updateDisplayNameUsersDisplayNamePatchMutation(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: getUserUsersMeGetQueryKey(),
      })
      onOpenChange(false)
    },
    onError: () => {
      setError('There is a problem. Try again.')
    },
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) {
      setError('Enter a name')
      return
    }
    patchDisplayName({ body: { display_name: trimmed } })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={submit}>
          <div
            className={`govuk-form-group ${error ? 'govuk-form-group--error' : ''}`}
          >
            <DialogTitle className="govuk-heading-m govuk-!-margin-bottom-0">
              <div className="govuk-label-wrapper">
                <label
                  className="govuk-label govuk-label--m"
                  htmlFor="display-name"
                >
                  Change name
                </label>
              </div>
            </DialogTitle>
            <div id="display-name-hint" className="govuk-hint">
              Change the display name for your profile
            </div>
            {error && (
              <p className="govuk-error-message" id="display-name-error">
                <span className="govuk-visually-hidden">Error:</span> {error}
              </p>
            )}
            <input
              className={`govuk-input bg-white ${error ? 'govuk-input--error' : ''}`}
              id="display-name"
              name="display-name"
              type="text"
              maxLength={100}
              value={name}
              aria-invalid={error ? true : undefined}
              aria-describedby={
                error ? 'display-name-error' : 'display-name-hint'
              }
              onChange={(e) => {
                setName(e.target.value)
                if (error) setError(null)
              }}
            />
          </div>
          <div className="govuk-button-group govuk-!-margin-top-4 justify-end">
            <button
              type="button"
              className="govuk-button govuk-button--secondary"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancel
            </button>
            <button type="submit" className="govuk-button" disabled={isPending}>
              {isPending && <Loader2 className="size-4 animate-spin" />}
              Save
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
