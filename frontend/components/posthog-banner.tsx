'use client'

import { FeatureFlags } from '@/lib/feature-flags'
import Link from 'next/link'
import { useFeatureFlagPayload } from 'posthog-js/react'

export function PosthogBanner() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let payload: any = useFeatureFlagPayload(FeatureFlags.ShowIssueBanner)

  if (!payload) {
    payload = {
      title: 'Important',
      message:
        'There is a problem with Minute. Our team is working to resolve this issue as quickly as possible. We apologise for any inconvenience',
      linkHref: 'https://minute.ai.gov.uk/',
      linkText: 'Learn more',
    }
  }

  return (
    <>
      <div
        className="govuk-notification-banner"
        role="region"
        aria-labelledby="govuk-notification-banner-title"
        data-module="govuk-notification-banner"
      >
        <div className="govuk-notification-banner__header">
          <h2
            className="govuk-notification-banner__title"
            id="govuk-notification-banner-title"
          >
            {payload.title || 'Important'}
          </h2>
        </div>
        <div className="govuk-notification-banner__content">
          <p className="govuk-notification-banner__heading">
            {payload.message ||
              'There is a problem with Minute. Our team is working to resolve this issue as quickly as possible. We apologise for any inconvenience'}
            {payload.linkHref && (
              <>
                {' '}
                <Link href={payload.linkHref} className="govuk-link">
                  {payload.linkText || 'Learn more'}
                </Link>
              </>
            )}
          </p>
        </div>
      </div>
    </>
  )
}
