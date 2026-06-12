'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

export const ServiceNavigation = () => {
  const pathname = usePathname()
  return (
    <section aria-label="Service information" className={`govuk-service-navigation ${pathname === '/' ? 'govuk-service-navigation--inverse' : ''}`} data-module="govuk-service-navigation">
      <div className="govuk-width-container">
        <div className="govuk-service-navigation__container">
          <span className="govuk-service-navigation__service-name">
            <Link href="/" className="govuk-service-navigation__link">
              Minute
            </Link>
          </span>
          <nav aria-label="Menu" className="govuk-service-navigation__wrapper">
            <button type="button" className="govuk-service-navigation__toggle govuk-js-service-navigation-toggle" aria-controls="navigation" hidden aria-hidden="true">
              Menu
            </button>
            <ul className="govuk-service-navigation__list" id="navigation">
              <li className={`govuk-service-navigation__item ${pathname.includes('/new') ? 'govuk-service-navigation__item--active' : ''}`}>
                <Link className="govuk-service-navigation__link" href="/new">
                  New transcription
                </Link>
              </li>
              <li className={`govuk-service-navigation__item ${pathname.includes('/transcriptions') ? 'govuk-service-navigation__item--active' : ''}`}>
                <Link className="govuk-service-navigation__link" href="/transcriptions">
                  Saved transcriptions
                </Link>
              </li>
              <li className={`govuk-service-navigation__item ${pathname.includes('/templates') ? 'govuk-service-navigation__item--active' : ''}`}>
                <Link className="govuk-service-navigation__link" href="/templates">
                  Templates
                </Link>
              </li>
              <li className={`govuk-service-navigation__item ${pathname.includes('/recordings') ? 'govuk-service-navigation__item--active' : ''}`}>
                <Link className="govuk-service-navigation__link" href="/recordings">
                  Offline recordings
                </Link>
              </li>
              <li className={`govuk-service-navigation__item ${pathname.includes('/settings') ? 'govuk-service-navigation__item--active' : ''}`}>
                <Link className="govuk-service-navigation__link" href="/settings">
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