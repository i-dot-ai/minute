'use client'

import { MinuteTab } from '@/app/transcriptions/[transcriptionId]/MinuteTab/MinuteTab'
import { TranscriptionTab } from '@/app/transcriptions/[transcriptionId]/TranscriptionTab/TranscriptionTab'
import { MinuteListItem, Transcription } from '@/lib/client'
import { useEffect, useRef } from 'react'

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

  useEffect(() => {
    const el = tabsRef.current
    if (!el) return

    let cancelled = false
    let tabsInstance: { teardown: () => void } | null = null

    import('govuk-frontend').then(({ Tabs }) => {
      if (cancelled) return
      tabsInstance = new Tabs(el)
    })

    return () => {
      cancelled = true
      tabsInstance?.teardown()
      el.removeAttribute('data-govuk-tabs-init')
    }
  }, [])

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
