'use client'

import { StartTranscriptionSection } from './start-transcription-section-2'
import { TranscriptionForm } from './types'
import { useFormContext } from 'react-hook-form'
import { Alert, AlertDescription } from '@/components/ui/alert'
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
  errorText,
  showMeetingDate = false,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  warningText?: string
  onConfirm: () => void
  disabled?: boolean
  errorText?: string
  showMeetingDate?: boolean
}) => {
  const form = useFormContext<TranscriptionForm>()
  // Check the date before confirming, so a half-typed date can't stop a live
  // recording or start a summary without it.
  const handleConfirm = async () => {
    if (showMeetingDate && !(await form.trigger('meeting_datetime'))) return
    onConfirm()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton={false}
        className="max-h-[calc(100dvh-2rem)] overflow-y-auto"
      >
        <DialogHeader>
          <DialogTitle className="govuk-heading-l">
            {warningText ? 'Transcribe meeting' : 'Generate summary'}
          </DialogTitle>
          {warningText && (
            <DialogDescription className="govuk-warning-text govuk-!-margin-bottom-0">
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
        {warningText && (
          <p className="govuk-body govuk-!-margin-bottom-0">
            You can select a new template later if needed
          </p>
        )}
        <StartTranscriptionSection showMeetingDate={showMeetingDate} />
        {errorText && (
          <Alert variant="destructive">
            <AlertDescription>{errorText}</AlertDescription>
          </Alert>
        )}
        <DialogFooter className="govuk-button-group sm:ml-auto sm:justify-end">
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
            onClick={handleConfirm}
          >
            {warningText ? 'Stop recording and save' : 'Generate summary'}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
