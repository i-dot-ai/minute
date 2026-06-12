'use client'

import { useGovukModule } from '@/hooks/use-govuk-module'
import { useRef } from 'react'

export const InstructionsTabs = () => {
  const tabsRef = useRef<HTMLDivElement>(null)

  useGovukModule(tabsRef, 'Tabs')

  return (
    <>
      <h2 className="govuk-heading-l">Instructions</h2>
      <div ref={tabsRef} className="govuk-tabs" data-module="govuk-tabs">
        <h3 className="govuk-tabs__title">
          Contents
        </h3>
        <ul className="govuk-tabs__list">
          <li className="govuk-tabs__list-item govuk-tabs__list-item--selected">
            <a className="govuk-tabs__tab" href="#windows">
              Windows
            </a>
          </li>
          <li className="govuk-tabs__list-item">
            <a className="govuk-tabs__tab" href="#macos">
              MacOS
            </a>
          </li>
        </ul>
        <div className="govuk-tabs__panel" id="windows">
          <h3 className="govuk-heading-m">Windows</h3>
          <ol className="govuk-list govuk-list--number">
            <li><strong>Choose your microphone</strong> - This microphone will
              record you and those in the room with you. Note that it will
              continue recording regardless of whether you are muted in the
              virutal meeting.</li>
            <li> <strong>Join your meeting</strong> - Join your meeting in Teams,
              Google Meet, Zoom.</li>
            <li><strong>Share your screen</strong> - When prompted, click the
              &quot;
              <strong>Entire Screen</strong>&quot; tab and select the screen
              where the meeting is showing.</li>
            <li><strong>Select &quot;Share Audio&quot;</strong>. Switch on the
              &quot;Share Audio&quot; the toggle in the bottom right of the share
              window.</li>
            <li><strong>Keep Minute open</strong> - It doesn&apos;t need to be
              visible on screen, but do not close Minute&apos;s tab</li>
          </ol>
        </div>
        <div className="govuk-tabs__panel govuk-tabs__panel--hidden" id="macos">
          <h3 className="govuk-heading-m">MacOS</h3>
          <ol className="govuk-list govuk-list--number">
            <li><strong>Choose your microphone</strong> - This microphone will
              record you and those in the room with you. Note that it will
              continue recording regardless of whether you are muted in the
              virutal meeting.</li>
            <li> <strong>Join your meeting</strong> - Join your meeting in Teams,
              Google Meet, Zoom.</li>
            <li><strong>Share the right tab</strong> - When prompted, select the
              tab where you have joined the meeting.</li>
            <li><strong>Select &quot;Share Audio&quot;</strong>. Switch on the
              &quot;Share Audio&quot; the toggle in the bottom right of the share
              window.</li>
            <li><strong>Keep both tabs open</strong> - Don&apos;t close either tab
              during recording. Switching between tabs is fine, but both must
              remain open.</li>
          </ol>
        </div>
      </div>
    </>
  )
}
