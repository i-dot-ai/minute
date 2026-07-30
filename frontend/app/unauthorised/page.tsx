'use client'
import { useIsOldUrl } from '@/hooks/use-is-old-url'
import React from 'react'

function Unauthorised(): React.JSX.Element {
  const isOldUrl = useIsOldUrl()
  return (
    <div className="govuk-width-container govuk-!-padding-top-4">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          {isOldUrl && (
            <div
              className="govuk-notification-banner"
              role="region"
              aria-labelledby="govuk-notification-banner-title"
              data-module="govuk-notification-banner"
            >
              <div className="govuk-notification-banner__header">
                <h2
                  className="govuk-notification-banner__title"
                  id="govuk-notification-banner-title"
                >
                  Important
                </h2>
              </div>
              <div className="govuk-notification-banner__content">
                <p className="govuk-notification-banner__heading">
                  This is an old Minute address. You may have access at our new
                  address,{' '}
                  <a
                    className="govuk-notification-banner__link"
                    href="https://minute.ai.gov.uk/"
                  >
                    minute.ai.gov.uk
                  </a>
                  .
                </p>
                <p className="govuk-body">
                  The new address has fewer access errors and works from any
                  network without a government VPN.
                </p>
              </div>
            </div>
          )}
          <h1 className="govuk-heading-xl">Unauthorised Access</h1>
          <p className="govuk-body">
            Sorry, you don&apos;t have permission to access this page.
          </p>
          <p className="govuk-body">
            If you believe this is an error, please contact us at{' '}
            <a className="govuk-link" href="mailto:minute-support@dsit.gov.uk">
              minute-support@dsit.gov.uk
            </a>
            .
          </p>
          <div className="govuk-button-group">
            <a
              href="https://minute.ai.gov.uk/"
              role="button"
              className="govuk-button"
            >
              Go to the home page
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Unauthorised
