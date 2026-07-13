import { ReactElement } from 'react'

export default function TranscriptionLayout({
  children,
}: {
  children: ReactElement
}) {
  return (
    <div className="govuk-main-wrapper">
      <div className="govuk-width-container">{children}</div>
    </div>
  )
}
