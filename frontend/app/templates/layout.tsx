import { FeatureFlags } from '@/lib/feature-flags'
import { getServerSideFeatureFlag } from '@/lib/posthog'
import { redirect } from 'next/navigation'
import { ReactElement } from 'react'

export default async function TemplatesLayout({
  children,
}: {
  children: ReactElement
}) {
  const userTemplatesEnabled = await getServerSideFeatureFlag(
    FeatureFlags.UserTemplatesEnabled
  )
  if (!userTemplatesEnabled) {
    redirect('/')
  }
  return children
}
