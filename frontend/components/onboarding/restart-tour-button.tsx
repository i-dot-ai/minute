'use client'

import { requestOnboardingTourRestart } from '@/hooks/use-onboarding-tour'

export function RestartTourButton() {
  return (
    <button
      type="button"
      className="govuk-link float-right text-(--govuk-link-colour)"
      onClick={requestOnboardingTourRestart}
    >
      Restart interactive tour
    </button>
  )
}
