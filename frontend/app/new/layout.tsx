import { ReactNode } from 'react'

export default function NewLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <div className="govuk-width-container govuk-main-wrapper">{children}</div>
    </>
  )
}
