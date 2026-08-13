import Link from 'next/link'

export const Header = async () => {
  return (
    <header>
      <div className="govuk-generic-header !bg-[#1d70b8]">
        <div className="govuk-generic-header__container govuk-width-container">
          <div className="govuk-generic-header__logo">
            <Link href="/" className="govuk-generic-header__homepage-link">
              <svg
                width="28"
                className="mr-2 inline-block"
                height="30"
                viewBox="0 0 28 30"
                fill="currentColor"
                xmlns="http://www.w3.org/2000/svg"
              >
                <rect x="2.8" y="11.5" width="2.1" height="7" rx="1.05" />
                <rect
                  x="7.875"
                  y="8.875"
                  width="2.1"
                  height="12.25"
                  rx="1.05"
                />
                <rect x="12.95" y="6.25" width="2.1" height="17.5" rx="1.05" />
                <rect
                  x="18.025"
                  y="8.875"
                  width="2.1"
                  height="12.25"
                  rx="1.05"
                />
                <rect x="23.1" y="11.5" width="2.1" height="7" rx="1.05" />
              </svg>
              Minute
            </Link>
          </div>
        </div>
      </div>
    </header>
  )
}
