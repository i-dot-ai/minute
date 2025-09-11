import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Transcription } from '@/lib/client'
import { CitationPopoverState } from '@/hooks/use-citation-popover'
import CitationPopoverContent from '@/app/transcriptions/[transcriptionId]/MinuteTab/components/editor/citation-popover'

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
    <Popover open={isPopoverOpen} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>
        <div
          style={{
            position: 'fixed',
            left: citationPopover.x,
            top: citationPopover.y,
            width: 1,
            height: 1,
          }}
        />
      </PopoverTrigger>
      <PopoverContent className="w-[600px]">
        {transcription?.dialogue_entries && (
          <CitationPopoverContent
            dialogueEntries={transcription.dialogue_entries}
            selectedIndex={citationPopover.index}
          />
        )}
      </PopoverContent>
    </Popover>
  )
}
