'use client'

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  archiveOrgOrganisationsOrgIdDeleteMutation,
  getMyOrganisationsUsersMeOrganisationsGetQueryKey,
  listOrganisationsOrganisationsGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

export const ArchiveOrgDialog = ({
  open,
  onOpenChange,
  orgId,
  orgName,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  orgId: string
  orgName: string
}) => {
  const queryClient = useQueryClient()
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  const { mutate: archiveOrg, isPending } = useMutation({
    ...archiveOrgOrganisationsOrgIdDeleteMutation(),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: listOrganisationsOrganisationsGetQueryKey(),
        }),
        queryClient.invalidateQueries({
          queryKey: getMyOrganisationsUsersMeOrganisationsGetQueryKey(),
        }),
      ])
      router.push('/organisations')
    },
    onError: () => setError('There is a problem. Try again.'),
  })

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="govuk-heading-l">
            Are you sure you want to archive this organisation?
          </AlertDialogTitle>
          <AlertDialogDescription className="govuk-body">
            Archiving hides the organisation and all of its content from its
            members. This cannot be undone from the app.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <p className="govuk-body govuk-!-font-weight-bold">{orgName}</p>
        {error && (
          <p className="govuk-error-message">
            <span className="govuk-visually-hidden">Error:</span> {error}
          </p>
        )}
        <AlertDialogFooter className="govuk-button-group sm:justify-end">
          <AlertDialogCancel asChild>
            <button
              type="button"
              className="govuk-button govuk-button--secondary !no-underline"
              disabled={isPending}
            >
              Cancel
            </button>
          </AlertDialogCancel>
          <button
            type="button"
            className="govuk-button govuk-button--warning"
            disabled={isPending}
            onClick={() => archiveOrg({ path: { org_id: orgId } })}
          >
            {isPending && <Loader2 className="size-4 animate-spin" />}
            Archive organisation
          </button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
