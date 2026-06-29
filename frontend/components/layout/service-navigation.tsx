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
      className="bg-(--govuk-surface-background-colour) fixed top-0 left-0 bottom-0"
    >
      <nav aria-label="Menu">
        <ul className="flex flex-col w-40" id="navigation">
          <li
            className={`govuk-service-navigation__service-name w-full ${pathname === '/' || pathname.includes('/new') ? 'bg-[#d2e2f1] font-bold text-black' : ''}`}
          >
            <Link
              href="/"
              className="ml-4 govuk-service-navigation__link flex items-center gap-2"
            >
              <AudioLines className="w-4 h-4" />
              Minute
            </Link>
          </li>
          <li
            className={`govuk-service-navigation__item w-full ${pathname.includes('/transcriptions') ? 'bg-[#d2e2f1] font-bold text-black' : ''}`}
          >
            <Link
              className="ml-4 govuk-service-navigation__link flex items-center gap-2"
              href="/transcriptions"
              data-onboarding="saved-transcriptions-nav"
            >
              <List className="w-4 h-4" />
              Transcriptions
            </Link>
          </li>
          <li
            className={`govuk-service-navigation__item w-full ${pathname.includes('/templates') ? 'bg-[#d2e2f1] font-bold text-black' : ''}`}
          >
            <Link
              className="ml-4 govuk-service-navigation__link flex items-center gap-2"
              href="/templates"
              data-onboarding="templates-nav"
            >
              <LayoutPanelTop className="w-4 h-4" />
              Templates
            </Link>
          </li>
        </ul>
      </nav>
    </section >
  )
}

export default ServiceNavigation
