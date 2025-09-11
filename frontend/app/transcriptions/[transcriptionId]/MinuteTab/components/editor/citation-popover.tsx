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
    <div className="max-h-[300px] space-y-2 overflow-y-auto p-2">
      {dialogueEntries.map((entry, index) => (
        <div
          key={index}
          ref={index === selectedIndex ? selectedRef : null}
          className={`${
            index === selectedIndex ? '-mx-2 bg-blue-50 px-2' : ''
          }`}
        >
          <div className="font-semibold">{entry.speaker}</div>
          <div>{entry.text}</div>
        </div>
      ))}
    </div>
  )
}
