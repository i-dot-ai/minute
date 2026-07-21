'use client'
import { GuardedLink } from '@/components/navigation/guarded-link'
import { usePathname } from 'next/navigation'
import { Bookmark, LayoutPanelTop, Mic } from 'lucide-react'
// import Image from 'next/image'

export const ServiceNavigation = () => {
  const pathname = usePathname()
  if (pathname === '/unauthorised') {
    return null
  }
  return (
    <section
      aria-label="Service information"
      className="flex h-full w-40 shrink-0 flex-col bg-(--govuk-surface-background-colour)"
    >
      <nav aria-label="Menu" className="flex h-full flex-col justify-between">
        <ul className="flex w-40 flex-col" id="navigation">
          <li
            className={`govuk-service-navigation__item w-full !border-l-4 !border-transparent ${pathname === '/' || pathname.includes('/new') ? '!border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
          >
            <GuardedLink
              href="/"
              aria-current={
                pathname === '/' || pathname.includes('/new')
                  ? 'page'
                  : undefined
              }
              className={`govuk-service-navigation__link ml-4 flex items-center gap-2 ${pathname === '/' || pathname.includes('/new') ? '!text-(--govuk-text-colour)' : ''}`}
            >
              {/* <Image src="/logos/minute-logo.svg" alt="" width={24} height={24} /> */}
              <Mic className="size-4" />
              Record
            </GuardedLink>
          </li>
          <li
            className={`govuk-service-navigation__item w-full !border-l-4 !border-transparent ${pathname.includes('/transcriptions') ? '!border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
          >
            <GuardedLink
              aria-current={
                pathname.includes('/transcriptions') ? 'page' : undefined
              }
              className={`govuk-service-navigation__link ml-4 flex items-center gap-2 ${pathname.includes('/transcriptions') ? '!text-(--govuk-text-colour)' : ''}`}
              href="/transcriptions"
              data-onboarding="saved-transcriptions-nav"
            >
              <Bookmark className="size-4" />
              Transcriptions
            </GuardedLink>
          </li>
          <li
            className={`govuk-service-navigation__item w-full !border-l-4 !border-transparent ${pathname.includes('/templates') ? '!border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
          >
            <GuardedLink
              aria-current={
                pathname.includes('/templates') ? 'page' : undefined
              }
              className={`govuk-service-navigation__link ml-4 flex items-center gap-2 ${pathname.includes('/templates') ? '!text-(--govuk-text-colour)' : ''}`}
              href="/templates"
              data-onboarding="templates-nav"
            >
              <LayoutPanelTop className="size-4" />
              Templates
            </GuardedLink>
          </li>
        </ul>
        <ul className="flex w-40 flex-col border-t border-(--govuk-border-colour)">
          <li
            className={`w-full !border-l-4 ${pathname.includes('/privacy') ? '!border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
          >
            <GuardedLink
              aria-current={pathname.includes('/privacy') ? 'page' : undefined}
              className="govuk-!-padding-top-2 govuk-!-padding-bottom-2 govuk-service-navigation__link ml-4 flex items-center gap-2 !text-[#484949]"
              href="/privacy"
            >
              Privacy
            </GuardedLink>
          </li>
          <li
            className={`w-full !border-l-4 ${pathname.includes('/support') ? '!border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
          >
            <GuardedLink
              aria-current={pathname.includes('/support') ? 'page' : undefined}
              className="govuk-!-padding-top-2 govuk-!-padding-bottom-2 govuk-service-navigation__link ml-4 flex items-center gap-2 !text-[#484949]"
              href="/support"
            >
              Support
            </GuardedLink>
          </li>
        </ul>
      </nav>
    </section>
  )
}

export default ServiceNavigation
