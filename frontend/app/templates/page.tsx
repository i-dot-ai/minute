import { UserTemplatesList } from '@/app/templates/components/user-templates-list'
import Link from 'next/link'

export default function TemplatesPage() {
  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <nav className="govuk-breadcrumbs govuk-!-margin-bottom-6" aria-label="Breadcrumb">
        <ol className="govuk-breadcrumbs__list">
          <li className="govuk-breadcrumbs__list-item">
            <Link className="govuk-breadcrumbs__link" href="/">Home</Link>
          </li>
        </ol>
      </nav>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl">Your templates</h1>
          <p className="govuk-body-l">
            Use templates to customise the structure and style of your minutes.
          </p>
          <UserTemplatesList />
        </div>
      </div>
    </div>
  )
}
