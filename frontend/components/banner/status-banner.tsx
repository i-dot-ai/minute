import { PosthogBannerPayload } from '@/components/banner/banner-controller'

export function StatusBanner({ payload }: { payload?: PosthogBannerPayload }) {
  const title =
    payload?.title ||
    'We are currently experiencing long processing times for recordings.'

  return (
    <div
      role="alert"
      className="govuk-!-padding-4 govuk-!-margin-bottom-4 bg-[#16548a] text-white"
    >
      <div className="govuk-warning-text govuk-!-margin-bottom-2">
        <span className="govuk-warning-text__icon" aria-hidden="true">
          !
        </span>
        <strong className="govuk-warning-text__text !text-white">
          <span className="govuk-visually-hidden">Warning</span>
          {title}
        </strong>
      </div>
      <p className="govuk-body govuk-!-margin-bottom-0 !text-white">
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
