'use client'

import { IssueBanner } from '@/components/banner/issue-banner'
import { StatusBanner } from '@/components/banner/status-banner'
import UrlMigrationBanner from '@/components/banner/url-migration-banner'
import { useIsOldUrl } from '@/hooks/use-is-old-url'
import { FeatureFlags } from '@/lib/feature-flags'
import posthog, { type JsonType } from 'posthog-js'
import { useFeatureFlagPayload } from 'posthog-js/react'

export type PosthogBannerPayload = JsonType & {
  title: string
  message?: string
  detailsText?: string
  messageItems?: string[]
  linkHref?: string
  linkText?: string
}

export function Banner() {
  const isOldUrl = useIsOldUrl()
  const showStatusBanner = true;
  const statusPayload = useFeatureFlagPayload(FeatureFlags.ShowStatusBanner) as
    | PosthogBannerPayload
    | undefined
  const issuePayload = useFeatureFlagPayload(FeatureFlags.ShowIssueBanner) as
    | PosthogBannerPayload
    | undefined

  const isDismissed =
    !!issuePayload &&
    localStorage.getItem('posthog-banner-dismissed') === issuePayload.title

  const handleDismiss = () => {
    posthog.capture('banner_dismissed')
    localStorage.setItem('posthog-banner-dismissed', issuePayload?.title || '')
    window.location.reload()
  }

  if (showStatusBanner) {
    return <StatusBanner payload={statusPayload} />
  }

  if (issuePayload && !isDismissed) {
    return <IssueBanner payload={issuePayload} onDismiss={handleDismiss} />
  }

  if (isOldUrl) {
    return <UrlMigrationBanner />
  }
  return null
}
