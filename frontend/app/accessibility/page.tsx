import accessibilityContent from '@/content/accessibility-statement.html'

export default function AccessibilityPage() {
  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div
          className="govuk-grid-column-two-thirds-from-desktop"
          dangerouslySetInnerHTML={{ __html: accessibilityContent }}
        />
      </div>
    </div>
  )
}
