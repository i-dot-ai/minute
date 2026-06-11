import Link from 'next/link'
import { PosthogBanner } from '@/components/posthog-banner'

export default function Home() {
  return (
    <>
      <div className="govuk-main-wrapper" style={{ backgroundColor: '#1d70b8' }}>
        <div className="govuk-width-container">
          <div className="govuk-grid-row">
            <div className="govuk-grid-column-two-thirds">
              <PosthogBanner />
              <h1 className="govuk-heading-xl govuk-!-margin-bottom-6" style={{ color: '#ffffff' }}>
                Minute
              </h1>
              <p className="govuk-body-l" style={{ color: '#ffffff' }}>
                Transcribe and summarise your meetings with AI. Suitable up to <span className="govuk-!-font-weight-bold">OFFICIAL SENSITIVE</span>.
              </p>
            </div>
          </div>
        </div>
      </div>
      <div className="govuk-main-wrapper">
        <div className="govuk-width-container">
          <div className="govuk-grid-row govuk-!-margin-bottom-6">
            <div className="govuk-grid-column-two-thirds">
              <h2 className="govuk-heading-l">Transcribe a new meeting</h2>
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
          <div style={{ borderBottom: '4px solid #1d70b8' }}></div>
          <div className="govuk-grid-row govuk-!-margin-top-6">
            <div className="govuk-grid-column-two-thirds">
              <h2 className="govuk-heading-l">Your transcriptions</h2>
              <Link href="/transcriptions" className="govuk-link">View all transcriptions</Link>
            </div>
          </div>
        </div>
      </div>

    </>
  )
}
