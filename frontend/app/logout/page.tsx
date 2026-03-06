import Link from 'next/link'

export default function LogoutPage() {
  return (
    <div className="govuk-width-container py-12">
      <main className="govuk-main-wrapper" id="main-content" role="main">
        <div className="govuk-grid-row flex justify-center">
          <div className="govuk-grid-column-two-thirds">
            <h1 className="govuk-heading-xl text-[var(--govuk-brand-colour)]">
              You have been signed out
            </h1>
            <p className="govuk-body">
              You have successfully signed out of Local Transcribe.
            </p>
            <div className="govuk-warning-text">
              <span className="govuk-warning-text__icon" aria-hidden="true">
                !
              </span>
              <strong className="govuk-warning-text__text">
                <span className="govuk-visually-hidden">Warning</span>
                For your security, you should now close your browser window.
              </strong>
            </div>
            <p className="govuk-body">
              This helps ensure that your authorised session is fully
              terminated.
            </p>
            <p className="govuk-body">
              <Link href="/" className="govuk-link">
                Sign back in
              </Link>
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
