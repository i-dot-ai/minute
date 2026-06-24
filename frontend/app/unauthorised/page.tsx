'use client'
import React from 'react'

function Unauthorised(): React.JSX.Element {
  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl">Unauthorised Access</h1>

          <p className="govuk-body">
            Sorry, you don&apos;t have permission to access this page.
          </p>
          <p className="govuk-body">
            If you believe this is an error, please contact us at{' '}
            <a
              className="govuk-link"
              href="mailto:minute-support@cabinetoffice.gov.uk"
            >
              minute-support@cabinetoffice.gov.uk
            </a>
            .
          </p>
          <div className="govuk-button-group">
            <a href="https://minute.ai.gov.uk/" role="button" className="govuk-button">
              Go to the home page
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Unauthorised
