'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

export const ServiceNavigation = () => {
  const pathname = usePathname()
  if (pathname === '/unauthorised') {
    return null
  }
  return (
    <section
      aria-label="Service information"
      className="govuk-service-navigation"
      data-module="govuk-service-navigation"
    >
      <div className="govuk-width-container">
        <div className="govuk-service-navigation__container">
          <nav aria-label="Menu" className="govuk-service-navigation__wrapper">
            <button
              type="button"
              className="govuk-service-navigation__toggle govuk-js-service-navigation-toggle"
              aria-controls="navigation"
              hidden
              aria-hidden="true"
            >
              Menu
            </button>
            <ul className="govuk-service-navigation__list" id="navigation">
              <li
                className={`govuk-service-navigation__item ${pathname === '/' || pathname.includes('/new') ? 'govuk-service-navigation__item--active' : ''}`}
              >
                <Link
                  className="govuk-service-navigation__link"
                  href="/new"
                  data-onboarding="new-transcription-nav"
                >
                  New meeting
                </Link>
              </li>
              <li
                className={`govuk-service-navigation__item ${pathname.includes('/transcriptions') ? 'govuk-service-navigation__item--active' : ''}`}
              >
                <Link
                  className="govuk-service-navigation__link"
                  href="/transcriptions"
                  data-onboarding="saved-transcriptions-nav"
                >
                  Transcriptions
                </Link>
              </li>
              <li
                className={`govuk-service-navigation__item ${pathname.includes('/templates') ? 'govuk-service-navigation__item--active' : ''}`}
              >
                <Link
                  className="govuk-service-navigation__link"
                  href="/templates"
                  data-onboarding="templates-nav"
                >
                  Templates
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
