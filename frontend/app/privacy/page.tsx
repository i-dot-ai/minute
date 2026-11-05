import privacyContent from '@/content/privacy-page.html'

export default function PrivacyPage() {
  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div
          className="govuk-grid-column-two-thirds"
          dangerouslySetInnerHTML={{ __html: privacyContent }}
        />
      </div>
      <h2 className="govuk-heading-m">Here is a new change</h2>
    </div>
  )
}
