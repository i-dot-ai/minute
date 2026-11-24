'use client'

import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import {
  getMyOrganisationsUsersMeOrganisationsGetQueryKey,
  getOrgOrganisationsOrgIdGetQueryKey,
  listOrganisationsOrganisationsGetQueryKey,
  updateOrgOrganisationsOrgIdPatchMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { FormEvent, useEffect, useState } from 'react'

export const RenameOrgDialog = ({
  open,
  onOpenChange,
  orgId,
  currentName,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  orgId: string
  currentName: string
}) => {
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  useEffect(() => {
    if (open) {
      setName(currentName)
      setError(null)
    }
  }, [open, currentName])

  const { mutate: renameOrg, isPending } = useMutation({
    ...updateOrgOrganisationsOrgIdPatchMutation(),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: getOrgOrganisationsOrgIdGetQueryKey({
            path: { org_id: orgId },
          }),
        }),
        queryClient.invalidateQueries({
          queryKey: listOrganisationsOrganisationsGetQueryKey(),
        }),
        queryClient.invalidateQueries({
          queryKey: getMyOrganisationsUsersMeOrganisationsGetQueryKey(),
        }),
      ])
      onOpenChange(false)
    },
    onError: () => setError('There is a problem. Try again.'),
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) {
      setError('Enter a name')
      return
    }
    renameOrg({ path: { org_id: orgId }, body: { name: trimmed } })
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
                  htmlFor="org-name"
                >
                  Rename organisation
                </label>
              </div>
            </DialogTitle>
            {error && (
              <p className="govuk-error-message" id="org-name-error">
                <span className="govuk-visually-hidden">Error:</span> {error}
              </p>
            )}
            <input
              className={`govuk-input bg-white ${error ? 'govuk-input--error' : ''}`}
              id="org-name"
              name="org-name"
              type="text"
              maxLength={255}
              value={name}
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? 'org-name-error' : undefined}
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
