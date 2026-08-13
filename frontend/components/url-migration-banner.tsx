const UrlMigrationBanner = () => {
  return (
    <div
      className="govuk-!-padding-4 govuk-!-margin-bottom-4 bg-[#16548a] text-white"
      role="region"
      aria-labelledby="notification-banner-title"
    >
      <h2
        className="govuk-heading-s !text-white"
        id="notification-banner-title"
      >
        Minute has a new home at{' '}
        <a href="https://minute.ai.gov.uk/" className="govuk-link !text-white">
          minute.ai.gov.uk
        </a>
      </h2>
      <p className="govuk-body govuk-!-margin-bottom-0 !text-white">
        The new address has fewer access errors and works from any network
        without a government VPN.
      </p>
    </div>
  )
}

export default UrlMigrationBanner
