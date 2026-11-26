'use client'

import { IssueBanner } from '@/components/banner/issue-banner'
import { StatusBanner } from '@/components/banner/status-banner'
import UrlMigrationBanner from '@/components/banner/url-migration-banner'
import { useIsOldUrl } from '@/hooks/use-is-old-url'
import { useProcessingStatus } from '@/hooks/use-processing-status'
import { processingAlert } from '@/lib/processing-status'
import { FeatureFlags } from '@/lib/feature-flags'
import posthog, { type JsonType } from 'posthog-js'
import { useFeatureFlagPayload } from 'posthog-js/react'
import { useEffect } from 'react'

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
  const { data } = useProcessingStatus()
  const { failing, slow, systemStatusTitle } = processingAlert(
    data?.last_10_minutes
  )
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

  const showStatusBanner = !!statusPayload || failing || slow

  useEffect(() => {
    if (showStatusBanner) {
      posthog.capture('status_banner_shown', {
        failedTranscripts: failing,
        longProcessingTimes: slow,
      })
    }
  }, [showStatusBanner, failing, slow])

  if (showStatusBanner) {
    return (
      <StatusBanner
        payload={statusPayload}
        systemStatusTitle={systemStatusTitle}
      />
    )
  }

  if (issuePayload && !isDismissed) {
    return <IssueBanner payload={issuePayload} onDismiss={handleDismiss} />
  }

  if (isOldUrl) {
    return <UrlMigrationBanner />
  }
  return null
}
