import Link from 'next/link'

export default function NewTranscriptPage() {
  return (
    <>
      <nav className="govuk-breadcrumbs govuk-!-margin-bottom-6" aria-label="Breadcrumb">
        <ol className="govuk-breadcrumbs__list">
          <li className="govuk-breadcrumbs__list-item">
            <Link className="govuk-breadcrumbs__link" href="/">Home</Link>
          </li>
        </ol>
      </nav>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl">Start a new transcription</h1>
          <ul className="govuk-list">
            <li className="homepage__list-item govuk-!-padding-top-2">
              <Link href="/new/upload" draggable="false" className="govuk-link govuk-!-font-weight-bold">
                Upload a file
              </Link>
              <p className="govuk-body govuk-!-margin-top-2">Upload a file from your computer.</p>
            </li>
            <li className="homepage__list-item govuk-!-padding-top-2">
              <Link href="/new/record-virtual" draggable="false" className="govuk-link govuk-!-font-weight-bold">
                Record a virtual meeting
              </Link>
              <p className="govuk-body govuk-!-margin-top-2">Capture audio from a virtual meeting in another tab.</p>
            </li>
            <li className="homepage__list-item govuk-!-padding-top-2">
              <Link href="/new/record-audio" draggable="false" className="govuk-link govuk-!-font-weight-bold">
                Record audio
              </Link>
              <p className="govuk-body govuk-!-margin-top-2">Record audio directly from your device.</p>
            </li>
          </ul>
        </div>
      </div>
    </>
  )
}
