import { NewTemplateDialog } from '@/app/templates/components/new-template-dialog'
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
            <h1 className="govuk-heading-xl govuk-!-margin-bottom-2" id="templates-list-heading">
              Templates
            </h1>
            <p className="govuk-body govuk-!-margin-bottom-6">
              Use templates to customise the structure and style of your minutes.
            </p>
            <div className="govuk-button-group">
              <NewTemplateDialog />
            </div>
            <Suspense fallback={<div>Loading...</div>}>
              <TemplatesTable />
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  )
}
