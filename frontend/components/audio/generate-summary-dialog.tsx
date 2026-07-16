'use client'

import { StartTranscriptionSection } from './start-transcription-section-2'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

export const GenerateSummaryDialog = ({
  open,
  onOpenChange,
  warningText,
  onConfirm,
  disabled = false,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  warningText?: string
  onConfirm: () => void
  disabled?: boolean
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent showCloseButton={false}>
        <DialogHeader>
          <DialogTitle className="govuk-heading-l">
            Generate summary
          </DialogTitle>
          {warningText && (
            <DialogDescription className="govuk-warning-text">
              <span className="govuk-warning-text__icon" aria-hidden="true">
                !
              </span>
              <strong className="govuk-warning-text__text">
                <span className="govuk-visually-hidden">Warning</span>
                {warningText}
              </strong>
            </DialogDescription>
          )}
        </DialogHeader>
        <StartTranscriptionSection />
        <DialogFooter className="govuk-button-group ml-auto sm:justify-end">
          <button
            type="button"
            className="govuk-button govuk-button--secondary"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </button>
          <button
            type="button"
            className="govuk-button"
            disabled={disabled}
            onClick={onConfirm}
          >
            Generate summary
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
