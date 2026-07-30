'use client'

import { FeatureFlags } from '@/lib/feature-flags'
import Link from 'next/link'
import { useFeatureFlagPayload } from 'posthog-js/react'

export function PosthogBanner() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const payload: any = useFeatureFlagPayload(FeatureFlags.ShowIssueBanner)


  if (!payload) {
    return null
  }

  const isDismissed = localStorage.getItem('posthog-banner-dismissed') === payload.title

  if (isDismissed) {
    return null
  }

  const handleDismiss = () => {
    localStorage.setItem('posthog-banner-dismissed', payload.title || '')
    window.location.reload()
  }

  return (
    <div
      className="bg-(--govuk-brand-colour) text-white govuk-!-padding-4 govuk-!-margin-bottom-4"
      role="region"
      aria-labelledby="notification-banner-title"
    >
      <div className="flex justify-between items-start">
        <h2
          className="govuk-heading-s !text-white"
          id="notification-banner-title"
        >
          {payload.title || 'Important'}
        </h2>
        <button className="govuk-link !text-white" onClick={handleDismiss}>Dismiss</button>
      </div>
      <details className="govuk-details govuk-!-margin-bottom-0">
        <summary className="govuk-details__summary before:!text-white">
          <span className="govuk-details__summary-text !text-white">
            {payload.detailsText || 'See details'}
          </span>
        </summary>
        <div className="govuk-details__text !text-white">
          {payload.message || ''}
          {
            payload.messageItems && (
              <ul className="govuk-list govuk-list--bullet">
                {payload.messageItems.map((item: string) => (
                  <li key={item} className="text-white">{item}</li>
                ))}
              </ul>
            )
          }
          {payload.linkHref && payload.linkText && (
            <Link href={payload.linkHref} className="govuk-link !text-white">
              {payload.linkText}
            </Link>
          )}
        </div>
      </details>
    </div>
  )
}
