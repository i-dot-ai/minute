'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { List, LayoutPanelTop, AudioLines } from 'lucide-react'

export const ServiceNavigation = () => {
  const pathname = usePathname()
  if (pathname === '/unauthorised') {
    return null
  }
  return (
    <section
      aria-label="Service information"
      className="fixed top-0 bottom-0 left-0 bg-(--govuk-surface-background-colour)"
    >
      <nav aria-label="Menu" className="flex h-full flex-col justify-between">
        <ul className="flex w-40 flex-col" id="navigation">
          <li
            className={`govuk-service-navigation__item w-full ${pathname === '/' || pathname.includes('/new') ? 'bg-[#d2e2f1] font-bold' : ''}`}
          >
            <a
              href="/"
              aria-current={
                pathname === '/' || pathname.includes('/new')
                  ? 'page'
                  : undefined
              }
              className={`govuk-service-navigation__link ml-4 flex items-center gap-2 ${pathname === '/' || pathname.includes('/new') ? '!text-black' : ''}`}
            >
              <AudioLines className="h-4 w-4" />
              Record
            </a>
          </li>
          <li
            className={`govuk-service-navigation__item w-full ${pathname.includes('/transcriptions') ? 'bg-[#d2e2f1] font-bold' : ''}`}
          >
            <Link
              aria-current={
                pathname.includes('/transcriptions') ? 'page' : undefined
              }
              className={`govuk-service-navigation__link ml-4 flex items-center gap-2 ${pathname.includes('/transcriptions') ? '!text-black' : ''}`}
              href="/transcriptions"
              data-onboarding="saved-transcriptions-nav"
            >
              <List className="h-4 w-4" />
              Transcriptions
            </Link>
          </li>
          <li
            className={`govuk-service-navigation__item w-full ${pathname.includes('/templates') ? 'bg-[#d2e2f1] font-bold' : ''}`}
          >
            <Link
              aria-current={
                pathname.includes('/templates') ? 'page' : undefined
              }
              className={`govuk-service-navigation__link ml-4 flex items-center gap-2 ${pathname.includes('/templates') ? '!text-black' : ''}`}
              href="/templates"
              data-onboarding="templates-nav"
            >
              <LayoutPanelTop className="h-4 w-4" />
              Templates
            </Link>
          </li>
        </ul>
        <ul className="flex w-40 flex-col border-t border-(--govuk-border-colour)">
          <li
            className={`w-full ${pathname.includes('/privacy') ? 'bg-[#d2e2f1] font-bold' : ''}`}
          >
            <Link
              aria-current={pathname.includes('/privacy') ? 'page' : undefined}
              className="govuk-!-padding-top-2 govuk-!-padding-bottom-2 govuk-service-navigation__link ${pathname.includes('/privacy') ? '!text-black' : ''} ml-4 flex items-center gap-2"
              href="/privacy"
            >
              Privacy
            </Link>
          </li>
          <li
            className={`w-full ${pathname.includes('/support') ? 'bg-[#d2e2f1] font-bold' : ''}`}
          >
            <Link
              aria-current={pathname.includes('/support') ? 'page' : undefined}
              className="govuk-!-padding-top-2 govuk-!-padding-bottom-2 govuk-service-navigation__link ${pathname.includes('/support') ? '!text-black' : ''} ml-4 flex items-center gap-2"
              href="/support"
            >
              Support
            </Link>
          </li>
        </ul>
      </nav>
    </section>
  )
}

export default ServiceNavigation
