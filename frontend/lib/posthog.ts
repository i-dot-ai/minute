import { FeatureFlags } from '@/lib/feature-flags'
import { cookies } from 'next/headers'
import { PostHog } from 'posthog-node'

export const getServerSideFeatureFlag = async (flagKey: FeatureFlags) => {
  const API_KEY = process.env.NEXT_PUBLIC_POSTHOG_API_KEY
  if (!API_KEY) {
    return undefined
  }
  const posthogClient = new PostHog(API_KEY, {
    host: 'https://eu.i.posthog.com',
    flushAt: 1,
    flushInterval: 0,
  })
  const cookiesStore = await cookies()
  const cookieName =
    'ph_' + process.env.NEXT_PUBLIC_POSTHOG_API_KEY + '_posthog'
  const cookieValue = cookiesStore.get(cookieName)?.value
  if (!cookieValue) {
    return false
  }
  const distinctId = JSON.parse(cookieValue).distinct_id
  if (!distinctId) {
    return false
  }
  const featureFlag = await posthogClient.isFeatureEnabled(flagKey, distinctId)
  return featureFlag || false
}
