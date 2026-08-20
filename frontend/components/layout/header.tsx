import Link from 'next/link'

export const Header = async () => {
  return (
    <header>
      <div className="govuk-generic-header !bg-[#1d70b8]">
        <div className="govuk-generic-header__container govuk-!-margin-left-6">
          <div className="govuk-!-padding-bottom-2 govuk-!-padding-top-2">
            <svg
              width={40}
              height={42.5}
              viewBox="0 0 28 30"
              fill="currentColor"
              className="govuk-!-margin-right-2 inline-block text-white"
              aria-hidden="true"
            >
              <rect x="2.8" y="11.5" width="2.1" height="7" rx="1.05" />
              <rect x="7.875" y="8.875" width="2.1" height="12.25" rx="1.05" />
              <rect x="12.95" y="6.25" width="2.1" height="17.5" rx="1.05" />
              <rect x="18.025" y="8.875" width="2.1" height="12.25" rx="1.05" />
              <rect x="23.1" y="11.5" width="2.1" height="7" rx="1.05" />
            </svg>
            <Link
              href="/"
              className="govuk-generic-header__homepage-link align-middle"
            >
              Minute
            </Link>
          </div>
        </div>
      </div>
    </header>
  )
}
