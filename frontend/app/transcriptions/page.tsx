import { DataRetentionSelect } from '@/components/recent-meetings/data-retention-select'
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
            <div className="flex items-center justify-between">
              <h1 className="govuk-heading-xl" id="transcriptions-list-heading">
                Transcriptions
              </h1>
              <DataRetentionSelect />
            </div>
            <Suspense fallback={<div>Loading...</div>}>
              <PaginatedTranscriptions />
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  )
}
