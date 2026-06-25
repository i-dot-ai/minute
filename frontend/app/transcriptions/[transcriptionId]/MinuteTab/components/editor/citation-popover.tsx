import { DialogueEntry } from '@/lib/client'
import React, { useEffect, useRef } from 'react'

interface CitationPopoverContentProps {
  dialogueEntries: DialogueEntry[]
  selectedIndex: number
}

export default function CitationPopoverContent({
  dialogueEntries,
  selectedIndex,
}: CitationPopoverContentProps) {
  const selectedRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (selectedRef.current) {
      selectedRef.current.scrollIntoView({ block: 'start' })
    }
  }, [selectedIndex])

  return (
    <div className="space-y-2">
      {dialogueEntries.map((entry, index) => (
        <div
          key={index}
          ref={index === selectedIndex ? selectedRef : null}
          className={`transcription-text-area ${
            index === selectedIndex ? 'transcription-text-area--playing' : ''
          }`}
        >
          <h2 className="govuk-heading-s">{entry.speaker}</h2>
          <p className="govuk-body">{entry.text}</p>
        </div>
      ))}
    </div>
  )
}
