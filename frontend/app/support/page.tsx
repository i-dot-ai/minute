import React from 'react'

export default function SupportPage() {
  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl">Support Center</h1>
          <h2 className="govuk-heading-l">Need Help?</h2>
          <p className="govuk-body">Contact our support team</p>
          <p className="govuk-body">
            Email us at:{' '}
            <a href="mailto:minute-support@cabinetoffice.gov.uk" className="govuk-link">
              minute-support@cabinetoffice.gov.uk
            </a>
          </p>

          <h2 className="govuk-heading-m">Response Time</h2>
          <p className="govuk-body">We aim to respond to all inquiries within 24 hours.</p>

          <h2 className="govuk-heading-m">Frequently Asked Questions</h2>

          <h3 className="govuk-heading-s">How do I start a new transcription?</h3>
          <p className="govuk-body">Upload your audio/video file or start a new recording directly from your browser.</p>
          <h3 className="govuk-heading-s">What file formats are supported?</h3>
          <p className="govuk-body">We support most common audio and video formats including MP3, WAV, MP4, and M4A.</p>
        </div>
      </div>
    </div>
  )
}
