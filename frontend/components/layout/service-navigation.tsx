'use client'
import { GuardedLink } from '@/components/navigation/guarded-link'
import { useParams, usePathname } from 'next/navigation'
import {
  Bookmark,
  ChevronDown,
  ChevronUp,
  LayoutPanelTop,
  Mic,
  Phone,
  LogOut,
} from 'lucide-react'
import { requestOnboardingTourRestart } from '@/hooks/use-onboarding-tour'
import { TranscriptMenu } from '@/components/layout/transcript-menu'
import { getTranscriptionTranscriptionsTranscriptionIdGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

export const ServiceNavigation = () => {
  const pathname = usePathname()
  const [isTranscriptDetailsCollapsed, setIsTranscriptDetailsCollapsed] =
    useState(false)
  const { transcriptionId } = useParams<{ transcriptionId?: string }>()
  const { data: transcription } = useQuery({
    ...getTranscriptionTranscriptionsTranscriptionIdGetOptions({
      path: { transcription_id: transcriptionId ?? '' },
    }),
    enabled: !!transcriptionId,
  })
  const noSummaries =
    !!transcription?.error || !!transcription?.no_speech_detected
  if (pathname === '/unauthorised') {
    return null
  }
  const pagesWithTour = ['/transcriptions', '/templates']
  const showTour =
    pathname === '/' || pagesWithTour.some((page) => pathname.includes(page))

  const isTranscriptDetailsPage =
    pathname.includes('/transcriptions/') &&
    !pathname.endsWith('/transcriptions')

  return (
    <div
      className="govuk-service-navigation govuk-service-navigation--side-nav"
      data-module="govuk-service-navigation"
    >
      <div className="govuk-width-container">
        <div className="govuk-service-navigation__container">
          <nav
            aria-label="Menu"
            className="govuk-service-navigation__wrapper flex w-full flex-wrap justify-between sm:items-center sm:justify-between md:block"
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
            {showTour && (
              <div className="govuk-!-margin-top-2 govuk-!-margin-bottom-2">
                <button
                  type="button"
                  className="govuk-service-navigation__link cursor-pointer text-(--govuk-link-colour) sm:mx-auto"
                  onClick={requestOnboardingTourRestart}
                >
                  Tour this page
                </button>
              </div>
            )}
            <ul
              className="govuk-service-navigation__list w-full"
              id="navigation"
            >
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
              <li>
                <div
                  className={`govuk-service-navigation__item !flex justify-between ${pathname.includes('/transcriptions') ? 'govuk-service-navigation__item--active' : ''}`}
                >
                  <GuardedLink
                    className="govuk-service-navigation__link"
                    href="/transcriptions"
                    aria-current={
                      pathname.includes('/transcriptions') ? 'page' : undefined
                    }
                  >
                    <Bookmark className="size-5" />
                    Transcriptions
                  </GuardedLink>
                  {isTranscriptDetailsPage && !noSummaries && (
                    <button
                      onClick={() =>
                        setIsTranscriptDetailsCollapsed((prev) => !prev)
                      }
                      className="govuk-service-navigation__link cursor-pointer hover:bg-[#8eb8dc]"
                      aria-expanded={!isTranscriptDetailsCollapsed}
                      aria-controls={
                        isTranscriptDetailsCollapsed
                          ? undefined
                          : 'transcript-details-menu'
                      }
                    >
                      {isTranscriptDetailsCollapsed ? (
                        <ChevronDown />
                      ) : (
                        <ChevronUp />
                      )}
                      <span className="govuk-visually-hidden">
                        {isTranscriptDetailsCollapsed ? 'Expand' : 'Collapse'}{' '}
                        transcript details
                      </span>
                    </button>
                  )}
                </div>
                {isTranscriptDetailsPage &&
                  !isTranscriptDetailsCollapsed &&
                  !noSummaries && <TranscriptMenu />}
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
              <li
                className={`govuk-service-navigation__item govuk-!-margin-top-8 sm:hidden! ${pathname.includes('/support') ? 'govuk-service-navigation__item--active' : ''}`}
              >
                <GuardedLink
                  className="govuk-service-navigation__link"
                  href="/support"
                  aria-current={
                    pathname.includes('/support') ? 'page' : undefined
                  }
                >
                  <Phone className="size-5" />
                  Contact us
                </GuardedLink>
              </li>
              <li className="govuk-service-navigation__item sm:hidden!">
                <GuardedLink
                  className="govuk-service-navigation__link"
                  href="/sign-out"
                  prefetch={false}
                >
                  <LogOut className="size-5" />
                  Sign out
                </GuardedLink>
              </li>
            </ul>
            <div className="mt-auto hidden w-full sm:block">
              {showTour && !noSummaries && (
                <div className="govuk-!-padding-top-3 govuk-!-padding-bottom-3">
                  <button
                    type="button"
                    className="govuk-service-navigation__link cursor-pointer text-(--govuk-link-colour) sm:mx-auto"
                    onClick={requestOnboardingTourRestart}
                  >
                    Tour this page
                  </button>
                </div>
              )}
            </div>
          </nav>
        </div>
      </div>
    </div>
  )
}

export default ServiceNavigation
