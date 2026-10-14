import React from 'react'

function genericError(): React.JSX.Element {
  return (
    <div className="govuk-main-wrapper govuk-width-container">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-l">An error occurred</h1>
          <div
            role="alert"
            className="govuk-!-padding-4 govuk-!-margin-bottom-4 govuk-!-margin-top-4 bg-[#e59a9a]"
          >
            <div className="govuk-warning-text">
              <span className="govuk-warning-text__icon" aria-hidden="true">
                !
              </span>
              <strong className="govuk-warning-text__text">
                <span className="govuk-visually-hidden">Warning</span>
                Something went wrong when accessing this page
              </strong>
            </div>
            <p className="govuk-body govuk-!-margin-bottom-0">
              Please try again later, or contact i.AI support if the issue
              persists.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default genericError
