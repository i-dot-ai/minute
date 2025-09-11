import { useState } from 'react'

export interface CitationPopoverState {
  index: number
  x: number
  y: number
}

export function useCitationPopover() {
  const [citationPopover, setCitationPopover] =
    useState<CitationPopoverState | null>(null)
  const [isPopoverOpen, setIsPopoverOpen] = useState(false)

  const handleCitationClick = (index: number, rect: DOMRect) => {
    setCitationPopover({ index, x: rect.left, y: rect.bottom })
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
