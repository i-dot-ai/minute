import { getServerPermissions } from '@/lib/server-permissions'
import { notFound } from 'next/navigation'
import { CreateOrgForm } from './create-org-form'

export default async function CreateOrgPage() {
  const permissions = await getServerPermissions()
  if (!permissions.includes('org.create')) {
    notFound()
  }

  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds-from-desktop">
          <h1 className="govuk-heading-l">Create an organisation</h1>
          <CreateOrgForm />
        </div>
      </div>
    </div>
  )
}
