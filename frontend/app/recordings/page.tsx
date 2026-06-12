import { OfflineRecordings } from '@/components/recent-meetings/offline-recordings'
import Link from 'next/link'
import { Suspense } from 'react'

export default function RecordingsPage() {
  return (
    <div className="govuk-main-wrapper">
      <div className="govuk-width-container">
        <nav className="govuk-breadcrumbs govuk-!-margin-bottom-6" aria-label="Breadcrumb">
          <ol className="govuk-breadcrumbs__list">
            <li className="govuk-breadcrumbs__list-item">
              <Link className="govuk-breadcrumbs__link" href="/">Home</Link>
            </li>
          </ol>
        </nav>
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-two-thirds-from-desktop">
            <h1 className="govuk-heading-xl">
              Offline recordings
            </h1>
            <p className="govuk-body-l">
              These are recording backups which are stored in this browser. We strongly recommend you delete or upload these so they are securely and reliably stored in the cloud.
            </p>
            <Suspense fallback={<div>Loading...</div>}>
              <OfflineRecordings />
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  )
}
