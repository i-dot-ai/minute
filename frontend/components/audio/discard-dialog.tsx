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
}: {
  open: boolean
  setOpen: Dispatch<SetStateAction<boolean>>
  onClickConfirm: () => void
}) => {
  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="govuk-heading-l">
            Are you sure you want to discard your recording?
          </AlertDialogTitle>
          <AlertDialogDescription className="govuk-body">
            Your recording has not been uploaded yet. Discarding it will delete
            the recording permanently.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="govuk-button-group sm:justify-start">
          <button
            type="button"
            onClick={onClickConfirm}
            className="govuk-button govuk-button--warning"
          >
            Discard recording
          </button>
          <AlertDialogCancel asChild>
            <button type="button" className="govuk-button govuk-button--secondary">
              Cancel
            </button>
          </AlertDialogCancel>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
