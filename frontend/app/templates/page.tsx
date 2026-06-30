import { UserTemplatesList } from '@/app/templates/components/user-templates-list'
import Link from 'next/link'

export default function TemplatesPage() {
  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-one-quarter">
          <h2 className="govuk-caption-m govuk-!-margin-bottom-1 govuk-!-margin-top-0 govuk-!-margin-bottom-3">
            Templates
          </h2>
          <nav>
            <ul className="govuk-list govuk-list--spaced">
              <li>
                <Link
                  className="govuk-link govuk-link--no-underline"
                  href="#document-templates"
                >
                  Document templates
                </Link>
              </li>
              <li>
                <Link
                  className="govuk-link govuk-link--no-underline"
                  href="#form-templates"
                >
                  Form templates
                </Link>
              </li>
            </ul>
          </nav>
        </div>
        <div
          className="govuk-grid-column-three-quarters"
          data-onboarding="templates-page"
        >
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
