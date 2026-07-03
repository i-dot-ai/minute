import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Dispatch, SetStateAction } from 'react'

export const DiscardConfirmDialog = ({
  open,
  setOpen,
  onClickConfirm,
  title = 'Are you sure you want to discard your recording?',
  description = 'Your recording has not been uploaded yet. Discarding it will delete the recording permanently.',
  confirmLabel = 'Discard recording',
}: {
  open: boolean
  setOpen: Dispatch<SetStateAction<boolean>>
  onClickConfirm: () => void
  title?: string
  description?: string
  confirmLabel?: string
}) => {
  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="govuk-heading-l">
            {title}
          </AlertDialogTitle>
          <AlertDialogDescription className="govuk-body">
            {description}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="govuk-button-group sm:justify-end">
          <AlertDialogCancel asChild>
            <button
              type="button"
              className="govuk-link text-(--govuk-link-colour)"
            >
              Cancel
            </button>
          </AlertDialogCancel>
          <button
            type="button"
            onClick={onClickConfirm}
            className="govuk-link link--warning"
          >
            {confirmLabel}
          </button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
