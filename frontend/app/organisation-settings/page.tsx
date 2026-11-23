'use client'

import { ChangeNameDialog } from '@/components/header/change-name-dialog'
import { OrganistaionDataRetentionDialog } from '@/components/settings/organisation-data-retention-dialog'
import { getUserUsersMeGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

export default function OrganisationSettings() {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  const [nameDialogOpen, setNameDialogOpen] = useState(false)

  return (
    <>
      <div className="govuk-width-container govuk-main-wrapper">
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-full">
            <h1 className="govuk-heading-l" id="organisation-settings">
              Organisation settings
            </h1>
            {user ? (
              <table
                className="govuk-table govuk-table--subtle govuk-!-margin-top-9"
                aria-labelledby="organisation-settings"
              >
                <thead className="govuk-table__head">
                  <tr className="govuk-table__row">
                    <th scope="col" className="govuk-table__header">
                      Account detail
                    </th>
                    <th scope="col" className="govuk-table__header">
                      Value
                    </th>
                    <th scope="col" className="govuk-table__header">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="govuk-table__body">
                  <tr className="govuk-table__row">
                    <th scope="row" className="govuk-table__header">
                      Name
                    </th>
                    <td className="govuk-table__cell">
                      Department for Business, Science, Innovation and Trade
                    </td>
                    <td className="govuk-table__cell">
                      <button
                        type="button"
                        className="govuk-link govuk-link--no-visited-state govuk-link--no-underline cursor-pointer text-(--govuk-link-colour)"
                      >
                        Change name
                      </button>
                    </td>
                  </tr>
                  <tr className="govuk-table__row">
                    <th scope="row" className="govuk-table__header">
                      Data retention period
                    </th>
                    <td className="govuk-table__cell">
                      Data retention policy not set (members can set their own)
                    </td>
                    <td className="govuk-table__cell">
                      <OrganistaionDataRetentionDialog user={user} />
                    </td>
                  </tr>
                </tbody>
              </table>
            ) : (
              <></>
            )}
          </div>
        </div>
      </div>
      <ChangeNameDialog
        open={nameDialogOpen}
        onOpenChange={setNameDialogOpen}
        displayName={user?.display_name}
      />
    </>
  )
}
