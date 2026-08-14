import Link from 'next/link'
import Image from 'next/image'

export const Header = async () => {
  return (
    <header>
      <div className="govuk-generic-header !bg-[#1d70b8]">
        <div className="govuk-generic-header__container govuk-!-margin-left-6">
          <div className="govuk-!-padding-bottom-2">
            <Image
              src="/logos/iAI-logo.png"
              alt="Minute"
              className="govuk-!-margin-right-2 inline-block"
              width={40}
              height={42.5}
            />
            <Link
              href="/"
              className="govuk-generic-header__homepage-link align-bottom"
            >
              Minute
            </Link>
          </div>
        </div>
      </div>
    </header>
  )
}
