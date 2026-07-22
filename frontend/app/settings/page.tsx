'use client'

import { SettingsForm } from '@/components/settings/settings-dialog'
import { getUserUsersMeGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'

export default function SettingsPage() {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  if (!user) {
    return (
      <div className="govuk-width-container govuk-!-padding-top-4">
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-two-thirds">
            <p className="govuk-body">Loading...</p>
          </div>
        </div>
      </div>
    )
  }
  return (
    <div className="govuk-width-container govuk-!-padding-top-4">
      <div className="govuk-grid-row">
        <div
          className="govuk-grid-column-two-thirds"
          data-onboarding="settings-page"
        >
          <h1 className="govuk-heading-l">Settings</h1>
          <SettingsForm user={user} />
        </div>
      </div>
    </div>
  )
}
