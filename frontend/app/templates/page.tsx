import { TemplatesTable } from '@/app/templates/components/templates-table'
import { Suspense } from 'react'

export default function TemplatesPage() {
  return (
    <div className="govuk-main-wrapper govuk-!-padding-bottom-0 h-[calc(100vh-61px)] overflow-hidden">
      <div className="govuk-width-container flex h-full min-h-0 flex-col">
        <Suspense fallback={<div>Loading...</div>}>
          <TemplatesTable />
        </Suspense>
      </div>
    </div>
  )
}
