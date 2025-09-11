'use client'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { FeatureFlags } from '@/lib/feature-flags'
import { Info, TriangleAlert } from 'lucide-react'
import { useFeatureFlagPayload } from 'posthog-js/react'

function Icon({ type }: { type: string }) {
  if (type === 'warning') {
    return <TriangleAlert />
  }
  return <Info />
}

export function PosthogBanner() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const payload: any = useFeatureFlagPayload(FeatureFlags.ShowIssueBanner)

  if (!payload) {
    return null
  }

  return (
    <Alert
      variant={payload.type === 'warning' ? 'destructive' : 'info'}
      className="my-4"
    >
      <Icon type={payload.type} />
      <AlertTitle>{payload.title || "Head's up!"}</AlertTitle>
      <AlertDescription>
        {payload.message ||
          'There is a problem with Minute. Our team is working to resolve this issue as quickly as possible. We apologise for any inconvenience'}
      </AlertDescription>
    </Alert>
  )
}
