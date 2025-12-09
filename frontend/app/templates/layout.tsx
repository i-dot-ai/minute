import { HistoryBackButton } from '@/components/ui/history-back-button'
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
  return (
    <div className="p-6 pt-1">
      <HistoryBackButton />
      {children}
    </div>
  )
}
