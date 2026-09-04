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
import { getUserTemplatesUserTemplatesGetQueryKey } from '@/lib/client/@tanstack/react-query.gen'
import { deleteUserTemplateUserTemplatesTemplateIdDelete } from '@/lib/client/sdk.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import posthog from 'posthog-js'
import { Dispatch, SetStateAction } from 'react'

export const DeleteTemplatesDialog = ({
  open,
  setOpen,
  templateIds,
  onDeleted,
}: {
  open: boolean
  setOpen: Dispatch<SetStateAction<boolean>>
  templateIds: string[]
  onDeleted: () => void
}) => {
  const queryClient = useQueryClient()
  const count = templateIds.length
  const { mutate: deleteTemplates, isPending } = useMutation({
    mutationFn: async (ids: string[]) => {
      await Promise.all(
        ids.map((id) =>
          deleteUserTemplateUserTemplatesTemplateIdDelete({
            path: { template_id: id },
          })
        )
      )
    },
    onSuccess: (_, ids) => {
      queryClient.invalidateQueries({
        queryKey: getUserTemplatesUserTemplatesGetQueryKey(),
      })
      posthog.capture('deleted_templates_bulk', { count: ids.length })
      setOpen(false)
      onDeleted()
    },
  })

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="govuk-heading-l">
            Are you sure you want to delete {count}{' '}
            {count === 1 ? 'template' : 'templates'}?
          </AlertDialogTitle>
          <AlertDialogDescription className="govuk-body">
            This will permanently delete the selected templates and cannot be
            undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="govuk-button-group sm:justify-start">
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
            onClick={() => deleteTemplates(templateIds)}
          >
            Delete
          </button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
