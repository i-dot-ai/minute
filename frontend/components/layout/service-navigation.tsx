'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

export const ServiceNavigation = () => {
  const pathname = usePathname()
  return (
    <section aria-label="Service information" className={`govuk-service-navigation ${pathname === '/' ? 'govuk-service-navigation--inverse' : ''}`} data-module="govuk-service-navigation">
      <div className="govuk-width-container">
        <div className="govuk-service-navigation__container">
          <span className={`govuk-service-navigation__service-name ${pathname === '/' ? 'govuk-!-margin-right-3' : ''}`}>
            <Link href="/" className={`govuk-service-navigation__link ${pathname === '/' ? 'govuk-!-padding-right-3' : ''}`}>
              Home
            </Link>
          </span>
          <nav aria-label="Menu" className="govuk-service-navigation__wrapper">
            <button type="button" className="govuk-service-navigation__toggle govuk-js-service-navigation-toggle" aria-controls="navigation" hidden aria-hidden="true">
              Menu
            </button>
            <ul className="govuk-service-navigation__list" id="navigation">
              <li className={`govuk-service-navigation__item ${pathname.includes('/new') ? 'govuk-service-navigation__item--active' : ''}`}>
                <Link
                  className="govuk-service-navigation__link"
                  href="/new"
                  data-onboarding="new-transcription-nav"
                >
                  New transcription
                </Link>
              </li>
              <li className={`govuk-service-navigation__item ${pathname.includes('/transcriptions') ? 'govuk-service-navigation__item--active' : ''}`}>
                <Link
                  className="govuk-service-navigation__link"
                  href="/transcriptions"
                  data-onboarding="saved-transcriptions-nav"
                >
                  Saved transcriptions
                </Link>
              </li>
              <li className={`govuk-service-navigation__item ${pathname.includes('/templates') ? 'govuk-service-navigation__item--active' : ''}`}>
                <Link
                  className="govuk-service-navigation__link"
                  href="/templates"
                  data-onboarding="templates-nav"
                >
                  Templates
                </Link>
              </li>
              <li className={`govuk-service-navigation__item ${pathname.includes('/recordings') ? 'govuk-service-navigation__item--active' : ''}`}>
                <Link
                  className="govuk-service-navigation__link"
                  href="/recordings"
                  data-onboarding="offline-recordings-nav"
                >
                  Incomplete recordings
                </Link>
              </li>
              <li className={`govuk-service-navigation__item ${pathname.includes('/settings') ? 'govuk-service-navigation__item--active' : ''}`}>
                <Link
                  className="govuk-service-navigation__link"
                  href="/settings"
                  data-onboarding="settings-nav"
                >
                  Settings
                </Link>
              </li>
            </ul>
          </nav>
        </div>
      </div>
    </section>
  )
}

export default ServiceNavigation