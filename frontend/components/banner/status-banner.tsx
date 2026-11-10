import { PosthogBannerPayload } from '@/components/banner/banner-controller'

export function StatusBanner({payload }: {payload?: PosthogBannerPayload}) {
  const title = payload?.title || 'We are currently experiencing long processing times for recordings.'

  return (
    <div
      role="alert"
      className="govuk-!-padding-4 govuk-!-margin-bottom-4 bg-[#e59a9a]"
    >
      <div className="govuk-warning-text">
        <span className="govuk-warning-text__icon" aria-hidden="true">
          !
        </span>
        <strong className="govuk-warning-text__text">
          <span className="govuk-visually-hidden">Warning</span>
          {title}
        </strong>
      </div>
      <p className="govuk-body govuk-!-margin-bottom-0">
        {payload?.message ||
          'We are working to resolve the issue as quickly as possible.'}{' '}
        Go to the{' '}
        <a href="/status" className="govuk-link !text-white">
          status page
        </a>{' '}
        to see the latest updates.
      </p>
    </div>
  )
}
