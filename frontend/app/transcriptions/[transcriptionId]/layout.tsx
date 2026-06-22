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
        <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
          <ol className="govuk-breadcrumbs__list">
            <li className="govuk-breadcrumbs__list-item">
              <Link href="/" className="govuk-breadcrumbs__link">
                Home
              </Link>
            </li>
            <li className="govuk-breadcrumbs__list-item">
              <Link href="/transcriptions" className="govuk-breadcrumbs__link">
                Transcriptions
              </Link>
            </li>
          </ol>
        </nav>
        {children}
      </div>
    </div>
  )
}
