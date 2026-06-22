import supportContent from '@/content/support-page.html'

export default function SupportPage() {
  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div
          className="govuk-grid-column-two-thirds"
          dangerouslySetInnerHTML={{ __html: supportContent }}
        />
      </div>
    </div>
  )
}
