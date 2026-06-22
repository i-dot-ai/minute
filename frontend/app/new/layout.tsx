import { ReactElement } from 'react'

export default function NewLayout({ children }: { children: ReactElement }) {
  return (
    <>
      <div className="govuk-width-container govuk-main-wrapper">{children}</div>
    </>
  )
}
