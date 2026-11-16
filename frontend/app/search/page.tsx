import type { Metadata } from 'next'
import { Suspense } from 'react'
import { SearchResults } from './search-results'

export const metadata: Metadata = { title: 'Search - Minute' }

export default function SearchPage() {
  return (
    <div className="govuk-main-wrapper govuk-width-container govuk-width-container--with-secondary-nav">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-three-quarters">
          <h1 className="govuk-heading-l">Search your transcriptions</h1>
          <Suspense
            fallback={
              <p className="govuk-body" role="status">
                Loading search…
              </p>
            }
          >
            <SearchResults />
          </Suspense>
        </div>
      </div>
    </div>
  )
}
