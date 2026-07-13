'use client'
import { GuardedLink } from '@/components/navigation/guarded-link'
import { usePathname } from 'next/navigation'
import { List, LayoutPanelTop, Plus } from 'lucide-react'

export const ServiceNavigation = () => {
  const pathname = usePathname()
  if (pathname === '/unauthorised') {
    return null
  }
  return (
    <section
      aria-label="Service information"
      className="sticky top-[61px] h-[calc(100vh-61px)] w-40 shrink-0 border-r border-(--govuk-surface-border-colour) bg-(--govuk-surface-background-colour)"
    >
      <nav aria-label="Menu" className="flex h-full flex-col justify-between">
        <ul className="flex w-40 flex-col" id="navigation">
          <li
            className={`govuk-service-navigation__item w-full !border-l-4 !border-transparent ${pathname === '/' || pathname.includes('/new') ? '!border-r-(--govuk-surface-border-colour) !border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
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
              <Plus className="size-4" />
              New meeting
            </GuardedLink>
          </li>
          <li
            className={`govuk-service-navigation__item w-full !border-l-4 !border-transparent ${pathname.includes('/transcriptions') ? '!border-r-(--govuk-surface-border-colour) !border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
          >
            <GuardedLink
              aria-current={
                pathname.includes('/transcriptions') ? 'page' : undefined
              }
              className={`govuk-service-navigation__link ml-4 flex items-center gap-2 ${pathname.includes('/transcriptions') ? '!text-(--govuk-text-colour)' : ''}`}
              href="/transcriptions"
              data-onboarding="saved-transcriptions-nav"
            >
              <List className="size-4" />
              Transcriptions
            </GuardedLink>
          </li>
          <li
            className={`govuk-service-navigation__item w-full !border-l-4 !border-transparent ${pathname.includes('/templates') ? '!border-r-(--govuk-surface-border-colour) !border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
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
        <ul className="flex w-40 flex-col">
          <li
            className={`w-full !border-l-4 ${pathname.includes('/privacy') ? '!border-r-(--govuk-surface-border-colour) !border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
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
            className={`w-full !border-l-4 ${pathname.includes('/support') ? '!border-r-(--govuk-surface-border-colour) !border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
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
