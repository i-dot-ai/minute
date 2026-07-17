import { DialogueEntry } from '@/lib/client'
import React, { useEffect, useRef } from 'react'
import { CircleUserRound } from 'lucide-react'

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
          <div className="govuk-!-margin-bottom-3 govuk-!-padding-top-1 flex items-center gap-2">
            <CircleUserRound />
            <h2 className="govuk-heading-s govuk-!-margin-bottom-0">
              {entry.speaker}
            </h2>
          </div>
          <p className="govuk-body">{entry.text}</p>
        </div>
      ))}
    </div>
  )
}
