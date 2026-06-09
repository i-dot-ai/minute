import Link from 'next/link'
import { PosthogBanner } from '@/components/posthog-banner'

export default function Home() {
  return (
    <div className="govuk-main-wrapper">
      <div className="govuk-width-container">
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-two-thirds">
            <PosthogBanner />
            <h1 className="govuk-heading-xl">
              Minute
            </h1>
            <p className="govuk-body-l">
              Transcribe and summarise your meetings with AI. Suitable up to <span className="govuk-!-font-weight-bold">OFFICIAL SENSITIVE</span>.
            </p>
            <ul className="govuk-list">
              <li className="homepage__list-item govuk-!-padding-top-2">
                <h2 className="govuk-heading-s govuk-!-margin-bottom-1">
                  <Link href="/new/upload" draggable="false" className="govuk-link">
                    Upload a file
                  </Link>
                </h2>
                <p className="govuk-body">Upload a file from your computer.</p>
              </li>
              <li className="homepage__list-item govuk-!-padding-top-2">
                <h2 className="govuk-heading-s govuk-!-margin-bottom-1">
                  <Link href="/new/record-virtual" draggable="false" className="govuk-link">
                    Record a virtual meeting
                  </Link>
                </h2>
                <p className="govuk-body">Capture audio from a virtual meeting in another tab.</p>
              </li>
              <li className="homepage__list-item govuk-!-padding-top-2">
                <h2 className="govuk-heading-s govuk-!-margin-bottom-1">
                  <Link href="/new/record-audio" draggable="false" className="govuk-link">
                    Record audio
                  </Link>
                </h2>
                <p className="govuk-body">Record audio directly from your device.</p>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
