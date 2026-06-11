import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Trash2 } from 'lucide-react'
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
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <h1 className="govuk-heading-l">
          Are you sure you want to discard your recording?
        </h1>
        <p className="govuk-body">
          Your recording has not been uploaded yet. Discarding it will delete
          the recording permanently.
        </p>
        <div className="govuk-button-group">
          <button
            type="button"
            onClick={onClickConfirm}
            className="govuk-button govuk-button--warning"
          >
            Discard recording
          </button>
          <button
            type="button"
            className="govuk-button govuk-button--secondary"
            onClick={() => setOpen(false)}
          >
            Cancel
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
