import Link from 'next/link'

export default function NewTranscriptPage() {
  return (
    <>
      <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
        <ol className="govuk-breadcrumbs__list">
          <li className="govuk-breadcrumbs__list-item">
            <Link className="govuk-breadcrumbs__link" href="/">
              Home
            </Link>
          </li>
        </ol>
      </nav>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl">Start a new transcription</h1>
          <p className="govuk-body-l">
            There are three ways to start a new transcription:
          </p>
        </div>
      </div>
      <div className="govuk-grid-row" data-onboarding="new-transcription-page">
        <div className="govuk-grid-column-one-third govuk-!-margin-bottom-4">
          <div className="govuk-!-padding-4 bg-[#8eb8dc]">
            <h2 className="govuk-heading-l">Record an in person meeting</h2>
            <div className="govuk-button-group">
              <Link
                href="/new/record-audio"
                role="button"
                className="govuk-button govuk-button--start govuk-button--inverse govuk-!-margin-top-3"
              >
                Record audio
                <svg
                  className="govuk-button__start-icon"
                  xmlns="http://www.w3.org/2000/svg"
                  width="17.5"
                  height="19"
                  viewBox="0 0 33 40"
                  aria-hidden="true"
                  focusable="false"
                >
                  <path fill="currentColor" d="M0 0h13l20 20-20 20H0l20-20z" />
                </svg>
              </Link>
            </div>
          </div>
        </div>
        <div className="govuk-grid-column-one-third govuk-!-margin-bottom-4">
          <div className="govuk-!-padding-4 bg-[#8eb8dc]">
            <h2 className="govuk-heading-l">Record a virtual meeting</h2>
            <div className="govuk-button-group">
              <Link
                href="/new/record-virtual"
                role="button"
                className="govuk-button govuk-button--start govuk-button--inverse govuk-!-margin-top-3"
              >
                Record a tab
                <svg
                  className="govuk-button__start-icon"
                  xmlns="http://www.w3.org/2000/svg"
                  width="17.5"
                  height="19"
                  viewBox="0 0 33 40"
                  aria-hidden="true"
                  focusable="false"
                >
                  <path fill="currentColor" d="M0 0h13l20 20-20 20H0l20-20z" />
                </svg>
              </Link>
            </div>
          </div>
        </div>
        <div className="govuk-grid-column-one-third govuk-!-margin-bottom-4">
          <div className="govuk-!-padding-4 bg-[#8eb8dc]">
            <h2 className="govuk-heading-l">
              Upload a file from your computer
            </h2>
            <div className="govuk-button-group">
              <Link
                href="/new/upload"
                draggable
                role="button"
                className="govuk-button govuk-button--start govuk-button--inverse govuk-!-margin-top-3"
              >
                Upload a file
                <svg
                  className="govuk-button__start-icon"
                  xmlns="http://www.w3.org/2000/svg"
                  width="17.5"
                  height="19"
                  viewBox="0 0 33 40"
                  aria-hidden="true"
                  focusable="false"
                >
                  <path fill="currentColor" d="M0 0h13l20 20-20 20H0l20-20z" />
                </svg>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
