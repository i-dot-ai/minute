'use client'
import { GuardedLink } from '@/components/navigation/guarded-link'
import { usePathname, useParams } from 'next/navigation'
import { Bookmark, LayoutPanelTop, Mic } from 'lucide-react'
import { requestOnboardingTourRestart } from '@/hooks/use-onboarding-tour'

export const ServiceNavigation = () => {
  const pathname = usePathname()
  const params = useParams()
  if (pathname === '/unauthorised') {
    return null
  }
  const pagesWithTour = ['/transcriptions', '/templates']
  const showTour =
    pathname === '/' || pagesWithTour.some((page) => pathname.includes(page))

  return (
    <div
      className="govuk-service-navigation govuk-service-navigation--side-nav"
      data-module="govuk-service-navigation"
    >
      <div className="govuk-width-container">
        <div className="govuk-service-navigation__container">
          <nav
            aria-label="Menu"
            className="govuk-service-navigation__wrapper sm:flex sm:items-center sm:justify-between md:block"
          >
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
                <GuardedLink
                  className="govuk-service-navigation__link"
                  href="/"
                  aria-current={
                    pathname === '/' || pathname.includes('/new')
                      ? 'page'
                      : undefined
                  }
                >
                  <Mic className="size-5" />
                  Record
                </GuardedLink>
              </li>
              <li
                className={`govuk-service-navigation__item ${pathname.includes('/transcriptions') ? 'govuk-service-navigation__item--active' : ''}`}
              >
                <GuardedLink
                  className="govuk-service-navigation__link"
                  href="/transcriptions"
                  aria-current={
                    pathname.includes('/transcriptions') ? 'page' : undefined
                  }
                >
                  <Bookmark className="size-5" />
                  Transcripts
                </GuardedLink>
              </li>
              <li
                className={`govuk-service-navigation__item ${pathname.includes('/templates') ? 'govuk-service-navigation__item--active' : ''}`}
              >
                <GuardedLink
                  className="govuk-service-navigation__link"
                  href="/templates"
                  aria-current={
                    pathname.includes('/templates') ? 'page' : undefined
                  }
                >
                  <LayoutPanelTop className="size-5" />
                  Templates
                </GuardedLink>
              </li>
            </ul>
            <div>
              {showTour && (
                <div className="govuk-!-padding-top-2 govuk-!-padding-bottom-2">
                  <button
                    type="button"
                    className="govuk-service-navigation__link cursor-pointer text-(--govuk-link-colour) sm:mx-auto"
                    onClick={requestOnboardingTourRestart}
                  >
                    Tour this page
                  </button>
                </div>
              )}
              <ul className="govuk-service-navigation__list govuk-service-navigation__list--footer">
                <li
                  className={`govuk-service-navigation__item ${pathname.includes('/privacy') ? 'govuk-service-navigation__item--active' : ''}`}
                >
                  <GuardedLink
                    className="govuk-service-navigation__link"
                    href="/privacy"
                  >
                    Privacy
                  </GuardedLink>
                </li>
                <li
                  className={`govuk-service-navigation__item ${pathname.includes('/support') ? 'govuk-service-navigation__item--active' : ''}`}
                >
                  <GuardedLink
                    className="govuk-service-navigation__link"
                    href="/support"
                  >
                    Contact
                  </GuardedLink>
                </li>
              </ul>
            </div>
          </nav>
        </div>
      </div>
    </div>
  )
}

export default ServiceNavigation
