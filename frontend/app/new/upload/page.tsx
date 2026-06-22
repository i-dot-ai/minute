import { AudioUploadForm } from '@/components/audio/AudioUploadForm'
import Link from 'next/link'

export default function RecordAudio() {
  return (
    <>
      <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
        <ol className="govuk-breadcrumbs__list">
          <li className="govuk-breadcrumbs__list-item">
            <Link className="govuk-breadcrumbs__link" href="/">
              Home
            </Link>
          </li>
          <li className="govuk-breadcrumbs__list-item">
            <Link className="govuk-breadcrumbs__link" href="/new">
              New transcription
            </Link>
          </li>
        </ol>
      </nav>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl">Upload a file</h1>
        </div>
      </div>
      <AudioUploadForm />
    </>
  )
}
