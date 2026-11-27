'use client'

import { ChangeNameDialog } from '@/components/header/change-name-dialog'
import { SettingsDialog } from '@/components/settings/settings-dialog'
import { getUserUsersMeGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'

export default function ProfilePage() {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  const [nameDialogOpen, setNameDialogOpen] = useState(false)

  return (
    <>
      <div className="govuk-width-container govuk-main-wrapper">
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-two-thirds-from-desktop">
            <h1 className="govuk-heading-l" id="your-account">
              Your account
            </h1>
            {user ? (
              <>
                <table
                  className="govuk-table govuk-table--subtle govuk-!-margin-top-9"
                  aria-label="account-details"
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
                      <td className="govuk-table__cell">{user.display_name}</td>
                      <td className="govuk-table__cell">
                        {' '}
                        <button
                          type="button"
                          className="govuk-link govuk-link--no-visited-state govuk-link--no-underline cursor-pointer text-(--govuk-link-colour)"
                          onClick={() => {
                            setNameDialogOpen(true)
                          }}
                        >
                          Change name
                        </button>
                      </td>
                    </tr>
                    <tr className="govuk-table__row">
                      <th scope="row" className="govuk-table__header">
                        Email
                      </th>
                      <td className="govuk-table__cell break-all">
                        {user.email}
                      </td>
                      <td className="govuk-table__cell">-</td>
                    </tr>
                  </tbody>
                </table>
                <table
                  id="settings"
                  className="govuk-table govuk-table--subtle govuk-!-margin-top-9"
                  aria-label="settings"
                >
                  <thead className="govuk-table__head">
                    <tr className="govuk-table__row">
                      <th scope="col" className="govuk-table__header">
                        Setting
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
                        Data retention period
                      </th>
                      <td className="govuk-table__cell">
                        {' '}
                        Transcriptions will be{' '}
                        {user.data_retention_days ? (
                          <>
                            deleted after {user.data_retention_days} day
                            {user.data_retention_days > 1 ? 's' : ''}
                          </>
                        ) : (
                          <>kept indefinitely</>
                        )}
                      </td>
                      <td className="govuk-table__cell">
                        <SettingsDialog user={user} />
                      </td>
                    </tr>
                  </tbody>
                </table>
              </>
            ) : (
              <p className="govuk-body">
                <Loader2 className="animate-spin" />
                Loading
              </p>
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
