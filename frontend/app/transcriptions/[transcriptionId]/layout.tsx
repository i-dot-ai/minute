import { ReactElement } from 'react'
import Link from 'next/link'

export default function TranscriptionLayout({
  children,
}: {
  children: ReactElement
}) {
  return (
    <div className="govuk-main-wrapper">
      <div className="govuk-width-container">
        {children}
      </div>
    </div>
  )
}
