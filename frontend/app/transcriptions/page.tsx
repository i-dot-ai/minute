import { PaginatedTranscriptions } from '@/components/recent-meetings/paginated-transcriptions'
import Link from 'next/link'
import { Suspense } from 'react'

export default function TranscriptionsPage() {
  return (
    <div className="govuk-main-wrapper">
      <div className="govuk-width-container">
        <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
          <ol className="govuk-breadcrumbs__list">
            <li className="govuk-breadcrumbs__list-item">
              <Link className="govuk-breadcrumbs__link" href="/">Home</Link>
            </li>
          </ol>
        </nav>
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-two-thirds-from-desktop" data-onboarding="saved-transcriptions-page">
            <h1 className="govuk-heading-xl">
              Saved transcriptions
            </h1>
            <Suspense fallback={<div>Loading...</div>}>
              <PaginatedTranscriptions />
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  )
}
