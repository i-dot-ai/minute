'use client'
import { GuardedLink } from '@/components/navigation/guarded-link'
import { useParams, usePathname } from 'next/navigation'
import {
  Bookmark,
  ChevronDown,
  ChevronUp,
  LayoutPanelTop,
  Mic,
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
              <div className="govuk-!-margin-top-2 govuk-!-margin-bottom-2 sm:hidden">
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
            </ul>
            <div className="hidden sm:block">
              <ul className="govuk-service-navigation__list">
                {showTour && !noSummaries && (
                  <li className="govuk-service-navigation__item govuk-service-navigation__item--small">
                    <button
                      type="button"
                      className="govuk-service-navigation__link cursor-pointer text-(--govuk-link-colour)"
                      onClick={requestOnboardingTourRestart}
                    >
                      Tour this page
                    </button>
                  </li>
                )}
                <li
                  className={`govuk-service-navigation__item govuk-service-navigation__item--small ${pathname.includes('/support') ? 'govuk-service-navigation__item--active' : ''}`}
                >
                  <GuardedLink
                    className="govuk-service-navigation__link"
                    href="/support"
                  >
                    Contact
                  </GuardedLink>
                </li>
              </ul>
              <ul className="govuk-service-navigation__list govuk-service-navigation__list--footer">
                <li
                  className={`govuk-service-navigation__item govuk-service-navigation__item--small ${pathname.includes('/legal') ? 'govuk-service-navigation__item--active' : ''}`}
                >
                  <GuardedLink
                    className="govuk-service-navigation__link"
                    href="/legal"
                  >
                    Legal
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
