'use client'
import { GuardedLink } from '@/components/navigation/guarded-link'
import { usePathname } from 'next/navigation'
import {
  Bookmark,
  LayoutPanelTop,
  Mic
} from 'lucide-react'
import { useState } from 'react'

export const ServiceNavigation = () => {
  const pathname = usePathname()
  if (pathname === '/unauthorised') {
    return null
  }
  return (
    <section
      aria-label="Service information"
      className="flex h-full shrink-0 flex-col bg-(--govuk-surface-background-colour)"
    >
      <nav aria-label="Menu" className="flex h-full flex-col justify-between">
        <ul className="flex flex-col w-24" id="navigation">
          <li
            className={`govuk-service-navigation__item govuk-!-margin-right-3 w-full !border-l-4 !border-transparent ${pathname === '/' || pathname.includes('/new') ? '!border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
          >
            <GuardedLink
              href="/"
              aria-current={
                pathname === '/' || pathname.includes('/new')
                  ? 'page'
                  : undefined
              }
              className={`govuk-service-navigation__link text-[0.875rem] flex flex-col items-center ${pathname === '/' || pathname.includes('/new') ? '!text-(--govuk-text-colour)' : ''}`}
            >
              <Mic className="size-5" />
              Record
            </GuardedLink>
          </li>
          <li
            className={`govuk-service-navigation__item govuk-!-margin-right-3 w-full !border-l-4 !border-transparent ${pathname.includes('/transcriptions') ? '!border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
          >
            <GuardedLink
              aria-current={
                pathname.includes('/transcriptions') ? 'page' : undefined
              }
              className={`govuk-service-navigation__link  text-[0.875rem] flex flex-col items-center ${pathname.includes('/transcriptions') ? '!text-(--govuk-text-colour)' : ''}`}
              href="/transcriptions"
              data-onboarding="saved-transcriptions-nav"
            >
              <Bookmark className="size-5" />
              Transcripts
            </GuardedLink>
          </li>
          <li
            className={`govuk-service-navigation__item govuk-!-margin-right-3 w-full !border-l-4 !border-transparent ${pathname.includes('/templates') ? '!border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
          >
            <GuardedLink
              aria-current={
                pathname.includes('/templates') ? 'page' : undefined
              }
              className={`govuk-service-navigation__link  text-[0.875rem] flex  flex-col items-center ${pathname.includes('/templates') ? '!text-(--govuk-text-colour)' : ''}`}
              href="/templates"
              data-onboarding="templates-nav"
            >
              <LayoutPanelTop className="size-5" />
              Templates
            </GuardedLink>
          </li>
        </ul>
        <div>
          {/* <button
            className={`govuk-link govuk-link--no-visited-state govuk-link--no-underline govuk-!-margin-bottom-2 ${isCollapsed ? 'govuk-!-padding-left-4' : 'govuk-!-padding-left-3'} flex flex-col items-center border-l-4 border-transparent text-(--govuk-link-colour)`}
            onClick={() => setIsCollapsed((prev) => !prev)}
          >
            {isCollapsed ? (
              <PanelLeftOpen className="size-5" />
            ) : (
              <>
                <PanelLeftClose className="size-5" />
                <span className={isCollapsed ? 'sr-only' : ''}>
                  {isCollapsed ? 'Expand' : 'Collapse'}
                </span>
              </>
            )}
          </button> */}
          <ul className="flex flex-col border-t border-(--govuk-border-colour)">
            <li
              className={`w-full !border-l-4 ${pathname.includes('/privacy') ? '!border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
            >
              <GuardedLink
                aria-current={
                  pathname.includes('/privacy') ? 'page' : undefined
                }
                className="govuk-!-padding-top-2 govuk-!-padding-bottom-2 govuk-service-navigation__link  text-[0.875rem] flex flex-col items-center !text-[#484949]"
                href="/privacy"
              >
                {/* <ShieldCheck className="size-5" /> */}
                Privacy
              </GuardedLink>
            </li>
            <li
              className={`w-full !border-l-4 ${pathname.includes('/support') ? '!border-l-(--govuk-brand-colour) bg-[#d2e2f1] font-bold' : ''}`}
            >
              <GuardedLink
                aria-current={
                  pathname.includes('/support') ? 'page' : undefined
                }
                className="govuk-!-padding-top-2 govuk-!-padding-bottom-2 govuk-service-navigation__link  text-[0.875rem] flex flex-col items-center !text-[#484949]"
                href="/support"
              >
                {/* <Mail className="size-5" /> */}
                Contact
              </GuardedLink>
            </li>
          </ul>
        </div>
      </nav>
    </section>
  )
}

export default ServiceNavigation
