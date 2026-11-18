import privacyContent from '@/content/privacy-page.html'
import Link from 'next/link'

export default function PrivacyPage() {
  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds-from-desktop">
          <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
            <ol className="govuk-breadcrumbs__list">
              <li className="govuk-breadcrumbs__list-item">
                <Link href="/legal" className="govuk-breadcrumbs__link">
                  Back
                </Link>
              </li>
            </ol>
          </nav>
          <div dangerouslySetInnerHTML={{ __html: privacyContent }} />
        </div>
      </div>
    </div>
  )
}
