'use client'

import { OrgMembers } from './org-members'
import { useAuthz } from '@/hooks/use-authz'
import { getOrgOrganisationsOrgIdGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useParams } from 'next/navigation'

export default function OrgPage() {
  const { org_id: orgId } = useParams<{ org_id: string }>()
  const { can, isLoading: authzLoading } = useAuthz()

  const { data: org, isLoading } = useQuery({
    ...getOrgOrganisationsOrgIdGetOptions({ path: { org_id: orgId } }),
    retry: false,
  })

  if (isLoading || authzLoading) {
    return (
      <div className="govuk-width-container govuk-main-wrapper">
        <p className="govuk-body">
          <Loader2 className="animate-spin" /> Loading
        </p>
      </div>
    )
  }

  if (!org) {
    return (
      <div className="govuk-width-container govuk-main-wrapper">
        <h1 className="govuk-heading-l">Organisation not found</h1>
        <p className="govuk-body">
          You do not have access to this organisation, or it does not exist.
        </p>
      </div>
    )
  }

  const canManageMembers = can('membership.manage', orgId)

  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds-from-desktop">
          <h1 className="govuk-heading-l">{org.name}</h1>
          {canManageMembers ? (
            <OrgMembers orgId={orgId} />
          ) : (
            <p className="govuk-body">
              You do not have permission to manage this organisation&rsquo;s
              members.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
