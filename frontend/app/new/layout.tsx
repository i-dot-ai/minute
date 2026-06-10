import { ReactElement } from 'react'
import Link from 'next/link'

export default function NewLayout({ children }: { children: ReactElement }) {
  return (
    <>
      <div className="govuk-width-container govuk-main-wrapper">
        <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
          <ol className="govuk-breadcrumbs__list">
            <li className="govuk-breadcrumbs__list-item">
              <Link className="govuk-breadcrumbs__link" href="/">Home</Link>
            </li>
          </ol>
        </nav>
        {children}
      </div>
    </>
  )
}
