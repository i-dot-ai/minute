'use client'

import CopyButton from '@/components/ui/copy-button'
import supportContent from '@/content/support-page.html'
import { getUserUsersMeGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'

export default function SupportPage() {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  const userId = user?.id

  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <div dangerouslySetInnerHTML={{ __html: supportContent }} />
          {userId && (
            <>
              <h2 className="govuk-heading-m">User id</h2>
              <p className="govuk-body">
                Please reference your user id in your email to us so we can look
                into your profile when responding to issues.
              </p>
              <div className="govuk-inset-text">
                <div className="flex items-center gap-2">
                  <p className="govuk-body govuk-!-margin-bottom-0">
                    <strong>Your user id:</strong> {userId}
                  </p>
                </div>
              </div>
              <CopyButton
                textToCopy={userId}
                posthogEvent="support_copy_user_id"
                label="Copy user id"
              />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
