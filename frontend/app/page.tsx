'use client'

import Link from 'next/link'
import { RestartTourButton } from '@/components/onboarding/restart-tour-button'
import { PosthogBanner } from '@/components/posthog-banner'
import { RecentOfflineRecordingsSection } from '@/components/recent-meetings/recent-offline-recordings-section'
import { RecentTranscriptions } from '@/components/recent-meetings/recent-transcriptions'
import { Suspense } from 'react'
import ExpiringSoonWarning from '@/components/expiring-soon-warning'
import UrlMigrationBanner from '@/components/url-migration-banner'
import { useIsOldUrl } from '@/hooks/use-is-old-url'

export default function Home() {
  const isOldUrl = useIsOldUrl()
  return (
    <>
      <div
        className="govuk-main-wrapper"
        style={{ backgroundColor: '#1d70b8' }}
      >
        <div className="govuk-width-container">
          <div className="govuk-grid-row flex h-full items-center justify-center">
            <div className="govuk-grid-column-two-thirds">
              <h1
                className="govuk-heading-xl govuk-!-margin-bottom-6"
                style={{ color: '#ffffff' }}
              >
                Minute
              </h1>
              <p className="govuk-body-l" style={{ color: '#ffffff' }}>
                Transcribe and summarise your meetings with AI. Suitable up to{' '}
                <span className="govuk-!-font-weight-bold">
                  OFFICIAL SENSITIVE
                </span>
                .
              </p>
              <div className="govuk-button-group">
                <a
                  href="/new"
                  role="button"
                  className="govuk-button govuk-button--start govuk-button--inverse"
                >
                  Start a new transcription
                  <svg
                    className="govuk-button__start-icon"
                    xmlns="http://www.w3.org/2000/svg"
                    width="17.5"
                    height="19"
                    viewBox="0 0 33 40"
                    aria-hidden="true"
                    focusable="false"
                  >
                    <path
                      fill="currentColor"
                      d="M0 0h13l20 20-20 20H0l20-20z"
                    />
                  </svg>
                </a>
              </div>
            </div>
            <div className="govuk-grid-column-one-third">
              <img
                src="/images/minute-icon-waveform.svg"
                alt=""
                className="w-full"
              />
            </div>
          </div>
        </div>
      </div>
      <div className="govuk-width-container govuk-main-wrapper">
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-full">
            <RestartTourButton />
          </div>
        </div>
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-full govuk-grid-column-two-thirds-from-desktop">
            {isOldUrl ? <UrlMigrationBanner /> : <PosthogBanner />}
            <Suspense fallback={null}>
              <RecentOfflineRecordingsSection />
            </Suspense>
            <h2 className="govuk-heading-l govuk-!-margin-top-6">
              Your recent transcriptions
            </h2>
            <Suspense fallback={null}>
              <ExpiringSoonWarning />
            </Suspense>
            <Suspense fallback={<div>Loading...</div>}>
              <RecentTranscriptions />
            </Suspense>
            <Link
              href="/transcriptions"
              className="govuk-link govuk-!-font-weight-bold govuk-!-margin-bottom-6"
            >
              View all transcriptions
            </Link>
          </div>
        </div>
      </div>
    </>
  )
}
