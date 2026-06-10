'use client'

import { MinuteTab } from '@/app/transcriptions/[transcriptionId]/MinuteTab/MinuteTab'
import { TranscriptionTab } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/TranscriptionTab'
import { useGovukModule } from '@/hooks/use-govuk-module'
import { MinuteListItem, Transcription } from '@/lib/client'
import { useRef } from 'react'

export function GovukTranscriptionTabs({
  transcription,
  minutes,
  selectedMinute,
}: {
  transcription: Transcription
  minutes: MinuteListItem[]
  selectedMinute: number
}) {
  const tabsRef = useRef<HTMLDivElement>(null)

  useGovukModule(tabsRef, 'Tabs')

  return (
    <div ref={tabsRef} className="govuk-tabs" data-module="govuk-tabs">
      <h2 className="govuk-tabs__title">Contents</h2>
      <ul className="govuk-tabs__list">
        <li className="govuk-tabs__list-item govuk-tabs__list-item--selected">
          <a className="govuk-tabs__tab" href="#summary">
            Summary
          </a>
        </li>
        <li className="govuk-tabs__list-item">
          <a className="govuk-tabs__tab" href="#transcript">
            Transcript
          </a>
        </li>
      </ul>
      <div className="govuk-tabs__panel" id="summary">
        <MinuteTab
          transcription={transcription}
          minutes={minutes}
          selectedMinute={selectedMinute}
        />
      </div>
      <div
        className="govuk-tabs__panel govuk-tabs__panel--hidden"
        id="transcript"
      >
        <TranscriptionTab transcription={transcription} />
      </div>
    </div>
  )
}
