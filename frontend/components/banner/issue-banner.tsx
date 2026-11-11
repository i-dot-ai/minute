'use client'

import posthog from 'posthog-js'
import Link from 'next/link'
import { type PosthogBannerPayload } from '@/components/banner/banner-controller'

export function IssueBanner({
  payload,
  onDismiss,
}: {
  payload: PosthogBannerPayload
  onDismiss: () => void
}) {
  return (
    <div
      className="govuk-!-padding-4 govuk-!-margin-bottom-4 bg-[#16548a] text-white"
      role="region"
      aria-labelledby="notification-banner-title"
    >
      <div className="flex items-start justify-between">
        <h2
          className="govuk-heading-s !text-white"
          id="notification-banner-title"
        >
          {payload.title || 'Important'}
        </h2>
        <button className="govuk-link !text-white" onClick={onDismiss}>
          Dismiss
        </button>
      </div>
      <details
        className="govuk-details govuk-!-margin-bottom-0"
        onToggle={(e) => {
          if (e.currentTarget.open) {
            posthog.capture('posthog_banner_details_expanded')
          }
        }}
      >
        <summary className="govuk-details__summary before:!text-white">
          <span className="govuk-details__summary-text !text-white">
            {payload.detailsText || 'See details'}
          </span>
        </summary>
        <div className="govuk-details__text !text-white">
          {payload.message || ''}
          {payload.messageItems && (
            <ul className="govuk-list govuk-list--bullet">
              {payload.messageItems.map((item: string) => (
                <li key={item} className="text-white">
                  {item}
                </li>
              ))}
            </ul>
          )}
          {payload.linkHref && payload.linkText && (
            <>
              {' '}
              <Link href={payload.linkHref} className="govuk-link !text-white">
                {payload.linkText}
              </Link>
            </>
          )}
        </div>
      </details>
    </div>
  )
}
