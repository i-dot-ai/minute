import { useState } from 'react'

export interface CitationPopoverState {
  index: number
}

export function useCitationPopover() {
  const [citationPopover, setCitationPopover] =
    useState<CitationPopoverState | null>(null)
  const [isPopoverOpen, setIsPopoverOpen] = useState(false)

  const handleCitationClick = (index: number) => {
    setCitationPopover({ index })
    setIsPopoverOpen(true)
  }

  const closeCitationPopover = () => {
    setIsPopoverOpen(false)
    setCitationPopover(null)
  }

  return {
    citationPopover,
    isPopoverOpen,
    handleCitationClick,
    closeCitationPopover,
    setIsPopoverOpen,
  }
}
