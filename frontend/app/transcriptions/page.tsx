import { PaginatedTranscriptions } from '@/components/recent-meetings/paginated-transcriptions'
import { Suspense } from 'react'

export default function TranscriptionsPage() {
  return (
    <div className="govuk-main-wrapper govuk-!-padding-bottom-0 h-[calc(100vh-61px)] overflow-hidden">
      <div className="govuk-width-container flex h-full min-h-0 flex-col">
        <div
          className="flex min-h-0 flex-1 flex-col"
          data-onboarding="saved-transcriptions-page"
        >
          <Suspense fallback={<div>Loading...</div>}>
            <PaginatedTranscriptions />
          </Suspense>
        </div>
      </div>
    </div>
  )
}
