import { DataRetentionSelect } from '@/components/recent-meetings/data-retention-select'
import { PaginatedTranscriptions } from '@/components/recent-meetings/paginated-transcriptions'
import { Suspense } from 'react'

export default function TranscriptionsPage() {
  return (
    <div className="govuk-main-wrapper">
      <div className="govuk-width-container">
        <div className="govuk-grid-row">
          <div
            className="govuk-grid-column-one-half"
            data-onboarding="saved-transcriptions-page"
          >
            <h1
              className="govuk-heading-l govuk-!-margin-bottom-3"
              id="transcriptions-list-heading"
            >
              Transcriptions
            </h1>
          </div>
          <div className="govuk-grid-column-one-half flex justify-end">
            <DataRetentionSelect />
          </div>
        </div>
        <Suspense fallback={<div>Loading...</div>}>
          <PaginatedTranscriptions />
        </Suspense>
      </div>
    </div>
  )
}
