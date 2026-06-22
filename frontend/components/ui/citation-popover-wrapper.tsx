'use client'

import CitationPopoverContent from '@/app/transcriptions/[transcriptionId]/MinuteTab/components/editor/citation-popover'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
} from '@/components/ui/dialog'
import { CitationPopoverState } from '@/hooks/use-citation-popover'
import { Transcription } from '@/lib/client'

interface CitationPopoverWrapperProps {
  citationPopover: CitationPopoverState | null
  isPopoverOpen: boolean
  onOpenChange: (open: boolean) => void
  transcription: Transcription
}

export function CitationPopoverWrapper({
  citationPopover,
  isPopoverOpen,
  onOpenChange,
  transcription,
}: CitationPopoverWrapperProps) {
  if (!citationPopover) return null

  return (
    <Dialog open={isPopoverOpen} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[85vh] flex-col gap-4 sm:max-w-2xl">
        <DialogTitle className="govuk-heading-m govuk-!-margin-bottom-0">
          Transcript excerpt
        </DialogTitle>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {transcription?.dialogue_entries && (
            <CitationPopoverContent
              dialogueEntries={transcription.dialogue_entries}
              selectedIndex={citationPopover.index}
            />
          )}
        </div>
        <DialogClose asChild>
          <button
            type="button"
            className="govuk-button govuk-button--secondary"
          >
            Close
          </button>
        </DialogClose>
      </DialogContent>
    </Dialog>
  )
}
