import { TemplatesTable } from '@/app/templates/components/templates-table'
import { Plus } from 'lucide-react'
import Link from 'next/link'
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
            <h1 className="govuk-heading-xl" id="templates-list-heading">
              Templates
            </h1>
            <div className="govuk-button-group">
              <Link
                className="govuk-button"
                role="button"
                href="/templates/new"
              >
                <Plus className="size-4" /> Generate new template
              </Link>
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
