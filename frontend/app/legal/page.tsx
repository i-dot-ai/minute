export default function LegalPage() {
  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds-from-desktop">
          <h1 className="govuk-heading-xl">Legal</h1>
          <p className="govuk-body">
            Use the links below to view the following documents:
          </p>
          <ul className="govuk-list govuk-list--bullet">
            <li>
              <a href="/legal/privacy" className="govuk-link">
                Privacy policy
              </a>
            </li>
            <li>
              <a href="/legal/accessibility" className="govuk-link">
                Accessibility statement
              </a>
            </li>
          </ul>
        </div>
      </div>
    </div>
  )
}
