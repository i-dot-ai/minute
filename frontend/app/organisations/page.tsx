'use client'

import { useAuthz } from '@/hooks/use-authz'
import { Loader2 } from 'lucide-react'
import Link from 'next/link'

export default function OrganisationsPage() {
  const { orgs, can, isLoading } = useAuthz()
  const canCreate = can('org.create')

  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds-from-desktop">
          <h1 className="govuk-heading-l">Organisations</h1>

          {isLoading ? (
            <p className="govuk-body">
              <Loader2 className="animate-spin" /> Loading
            </p>
          ) : orgs && orgs.length > 0 ? (
            <ul className="govuk-list">
              {orgs.map((org) => (
                <li key={org.id}>
                  <Link
                    href={`/organisations/${org.id}`}
                    className="govuk-link govuk-link--no-visited-state"
                  >
                    {org.name}
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="govuk-body">
              You are not a member of any organisations.
            </p>
          )}

          {canCreate && (
            <Link
              href="/organisations/new"
              className="govuk-button"
              data-module="govuk-button"
            >
              Create organisation
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}
