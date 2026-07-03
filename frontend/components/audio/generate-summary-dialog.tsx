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
  title,
  description,
  confirmLabel = 'Generate summary',
  onConfirm,
  disabled = false,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  confirmLabel?: string
  onConfirm: () => void
  disabled?: boolean
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent wideModal showCloseButton={false}>
        <DialogHeader>
          <DialogTitle className="govuk-heading-l">{title}</DialogTitle>
          {description && (
            <DialogDescription className="govuk-body">
              {description}
            </DialogDescription>
          )}
        </DialogHeader>
        <StartTranscriptionSection />
        <DialogFooter className="govuk-button-group ml-auto sm:justify-end">
          <button
            type="button"
            className="govuk-link text-(--govuk-link-colour)"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </button>
          <button
            type="button"
            className="govuk-button govuk-button--start"
            disabled={disabled}
            onClick={onConfirm}
          >
            {confirmLabel}
            <svg
              className="govuk-button__start-icon"
              xmlns="http://www.w3.org/2000/svg"
              width="17.5"
              height="19"
              viewBox="0 0 33 40"
              aria-hidden="true"
              focusable="false"
            >
              <path fill="currentColor" d="M0 0h13l20 20-20 20H0l20-20z" />
            </svg>
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
