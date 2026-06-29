import { PaginatedTranscriptions } from '@/components/recent-meetings/paginated-transcriptions'
import { Suspense } from 'react'

export default function TranscriptionsPage() {
  return (
    <div className="govuk-main-wrapper">
      <div className="govuk-width-container">
        <div className="govuk-grid-row">
          <div
            className="govuk-grid-column-full"
            data-onboarding="saved-transcriptions-page"
          >
            <h1 className="govuk-heading-xl">Saved transcriptions</h1>
            <Suspense fallback={<div>Loading...</div>}>
              <PaginatedTranscriptions />
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  )
}
