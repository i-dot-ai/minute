import { MicRecorderForm } from '@/components/audio/mic-recorder'
import Link from 'next/link'

export default function RecordAudio() {
  return (
    <>
      <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
        <ol className="govuk-breadcrumbs__list">
          <li className="govuk-breadcrumbs__list-item">
            <Link className="govuk-breadcrumbs__link" href="/">Home</Link>
          </li>
          <li className="govuk-breadcrumbs__list-item">
            <Link className="govuk-breadcrumbs__link" href="/new">New transcription</Link>
          </li>
        </ol>
      </nav>
      <h1 className="govuk-heading-xl">Record a meeting</h1>
      <MicRecorderForm />
    </>
  )
}
