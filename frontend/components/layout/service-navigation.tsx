'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

export const ServiceNavigation = () => {
  const pathname = usePathname()
  return (
    <section aria-label="Service information" className="govuk-service-navigation"
      data-module="govuk-service-navigation">
      <div className="govuk-width-container">
        <div className="govuk-service-navigation__container">
          <span className="govuk-service-navigation__service-name">
            <a href="/" className="govuk-service-navigation__link">
              Minute
            </a>
          </span>
          <nav aria-label="Menu" className="govuk-service-navigation__wrapper">
            <button type="button" className="govuk-service-navigation__toggle govuk-js-service-navigation-toggle" aria-controls="navigation" hidden aria-hidden="true">
              Menu
            </button>
            <ul className="govuk-service-navigation__list" id="navigation">
              <li className={`govuk-service-navigation__item ${pathname.includes('/meetings') ? 'govuk-service-navigation__item--active' : ''}`}>
                <Link className="govuk-service-navigation__link" href="/meetings">
                  Previous meetings
                </Link>
              </li>
              <li className={`govuk-service-navigation__item ${pathname.includes('/templates') ? 'govuk-service-navigation__item--active' : ''}`}>
                <Link className="govuk-service-navigation__link" href="/templates">
                  Templates
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