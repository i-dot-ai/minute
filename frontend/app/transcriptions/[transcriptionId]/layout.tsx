import { ReactElement } from 'react'

export default function TranscriptionLayout({
  children,
}: {
  children: ReactElement
}) {
  return (
    <div className="govuk-main-wrapper govuk-!-padding-bottom-0 h-[calc(100vh-61px)] overflow-hidden">
      <div className="govuk-width-container flex h-full min-h-0 flex-col">
        {children}
      </div>
    </div>
  )
}
