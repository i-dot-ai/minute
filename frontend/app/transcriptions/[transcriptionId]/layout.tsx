'use client'

import { ReactElement } from 'react'

export default function TranscriptionLayout({
  children,
}: {
  children: ReactElement
}) {
  return (
    <div className="govuk-width-container govuk-width-container--with-secondary-nav">
      {children}
    </div>
  )
}
