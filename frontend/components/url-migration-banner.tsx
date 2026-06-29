const UrlMigrationBanner = () => {
  return (
    <div
      className="govuk-notification-banner m-4"
      role="region"
      aria-labelledby="govuk-notification-banner-title"
      data-module="govuk-notification-banner"
    >
      <div className="govuk-notification-banner__header">
        <h2
          className="govuk-notification-banner__title"
          id="govuk-notification-banner-title"
        >
          Important
        </h2>
      </div>
      <div className="govuk-notification-banner__content">
        <p className="govuk-notification-banner__heading">
          Minute has a new home at{' '}
          <a href="https://minute.ai.gov.uk/" className="govuk-link">
            minute.ai.gov.uk
          </a>
        </p>
        <p className="govuk-body">
          The new address has fewer access errors and works from any network
          without a government VPN.
        </p>
      </div>
    </div>
  )
}

export default UrlMigrationBanner
