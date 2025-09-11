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
        <DialogHeader>
          <DialogTitle>
            Are you sure you want to discard your recording?
          </DialogTitle>
          <DialogDescription>
            Your recording has not been uploaded yet. Discarding it will delete
            the recording permanently.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="flex gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => setOpen(false)}
            className="h-12"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={onClickConfirm}
            className="h-12 hover:bg-red-800"
          >
            <Trash2 /> Discard recording
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
