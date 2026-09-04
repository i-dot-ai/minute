import { TemplatesTable } from '@/app/templates/components/templates-table'
import { Suspense } from 'react'

export default function TemplatesPage() {
  return (
    <div className="govuk-main-wrapper">
      <div className="govuk-width-container">
        <div className="govuk-grid-row">
          <div
            className="govuk-grid-column-full"
            data-onboarding="templates-page"
          >
            <h1
              className="govuk-heading-l govuk-!-margin-bottom-3"
              id="templates-list-heading"
            >
              Templates
            </h1>
            <p className="govuk-body">
              Use templates to customise the structure and style of your
              minutes.
            </p>
          </div>
        </div>
        <Suspense fallback={<div>Loading...</div>}>
          <TemplatesTable />
        </Suspense>
      </div>
    </div>
  )
}
