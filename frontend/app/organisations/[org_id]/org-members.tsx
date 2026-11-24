'use client'

import {
  addMemberRolesOrganisationsOrgIdMembersUserIdRolesPostMutation,
  addOrgMemberOrganisationsOrgIdMembersPostMutation,
  listAssignableRolesOrganisationsOrgIdAssignableRolesGetOptions,
  listOrgMembersOrganisationsOrgIdMembersGetOptions,
  listOrgMembersOrganisationsOrgIdMembersGetQueryKey,
  removeMemberRoleOrganisationsOrgIdMembersUserIdRolesRoleNameDeleteMutation,
  removeOrgMemberOrganisationsOrgIdMembersUserIdDeleteMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import type { OrgMembersResponse, RoleName } from '@/lib/client/types.gen'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { FormEvent, useState } from 'react'

export const OrgMembers = ({ orgId }: { orgId: string }) => {
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)

  const membersKey = listOrgMembersOrganisationsOrgIdMembersGetQueryKey({
    path: { org_id: orgId },
  })

  const { data: members, isLoading } = useQuery({
    ...listOrgMembersOrganisationsOrgIdMembersGetOptions({
      path: { org_id: orgId },
    }),
    retry: false,
  })

  const onMutated = (data: OrgMembersResponse) => {
    queryClient.setQueryData(membersKey, data)
    setError(null)
  }
  const onError = () => setError('There is a problem. Try again.')

  const { mutate: addMember, isPending: addingMember } = useMutation({
    ...addOrgMemberOrganisationsOrgIdMembersPostMutation(),
    onSuccess: (data) => {
      onMutated(data)
      setEmail('')
    },
    onError: (err) => {
      const detail = (err as { detail?: unknown })?.detail
      setError(
        detail === 'User not found'
          ? 'No account exists for that email address. The user must sign in at least once before they can be added.'
          : 'There is a problem. Try again.'
      )
    },
  })
  const { mutate: addRole } = useMutation({
    ...addMemberRolesOrganisationsOrgIdMembersUserIdRolesPostMutation(),
    onSuccess: onMutated,
    onError,
  })
  const { mutate: removeRole } = useMutation({
    ...removeMemberRoleOrganisationsOrgIdMembersUserIdRolesRoleNameDeleteMutation(),
    onSuccess: onMutated,
    onError,
  })
  const { mutate: removeMember } = useMutation({
    ...removeOrgMemberOrganisationsOrgIdMembersUserIdDeleteMutation(),
    onSuccess: onMutated,
    onError: () =>
      setError('Could not remove member. They may be the last admin.'),
  })

  const submitAddMember = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = email.trim()
    if (!trimmed) {
      setError('Enter an email address')
      return
    }
    addMember({
      path: { org_id: orgId },
      body: { email: trimmed },
    })
  }

  if (isLoading) {
    return (
      <p className="govuk-body">
        <Loader2 className="animate-spin" /> Loading members
      </p>
    )
  }

  const activeMembers = (members?.members ?? []).filter((m) => m.is_active)

  return (
    <>
      <h2 className="govuk-heading-m">Members</h2>
      {error && (
        <p className="govuk-error-message">
          <span className="govuk-visually-hidden">Error:</span> {error}
        </p>
      )}
      <table className="govuk-table" aria-label="organisation-members">
        <thead className="govuk-table__head">
          <tr className="govuk-table__row">
            <th scope="col" className="govuk-table__header">
              Email
            </th>
            <th scope="col" className="govuk-table__header">
              Roles
            </th>
            <th scope="col" className="govuk-table__header">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="govuk-table__body">
          {activeMembers.map((member) => (
            <tr className="govuk-table__row" key={member.user_id}>
              <td className="govuk-table__cell break-all">{member.email}</td>
              <td className="govuk-table__cell">
                <ul className="govuk-list govuk-!-margin-bottom-0">
                  {member.roles.map((role) => (
                    <li key={role}>
                      {role}{' '}
                      <button
                        type="button"
                        className="govuk-link govuk-link--no-visited-state cursor-pointer border-0 bg-transparent text-(--govuk-link-colour)"
                        onClick={() =>
                          removeRole({
                            path: {
                              org_id: orgId,
                              user_id: member.user_id,
                              role_name: role,
                            },
                          })
                        }
                      >
                        Remove
                      </button>
                    </li>
                  ))}
                </ul>
                <AddRoleControl
                  orgId={orgId}
                  existing={member.roles}
                  onAdd={(role) =>
                    addRole({
                      path: { org_id: orgId, user_id: member.user_id },
                      body: { roles: [role] },
                    })
                  }
                />
              </td>
              <td className="govuk-table__cell">
                <button
                  type="button"
                  className="govuk-link govuk-link--no-visited-state cursor-pointer border-0 bg-transparent text-(--govuk-link-colour)"
                  onClick={() =>
                    removeMember({
                      path: { org_id: orgId, user_id: member.user_id },
                    })
                  }
                >
                  Remove member
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="govuk-heading-m govuk-!-margin-top-6">Add a member</h2>
      <form onSubmit={submitAddMember}>
        <div className="govuk-form-group">
          <label className="govuk-label" htmlFor="add-member-email">
            Email address
          </label>
          <input
            className="govuk-input bg-white"
            id="add-member-email"
            name="add-member-email"
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value)
              if (error) setError(null)
            }}
          />
        </div>
        <button type="submit" className="govuk-button" disabled={addingMember}>
          {addingMember && <Loader2 className="size-4 animate-spin" />}
          Add member
        </button>
      </form>
    </>
  )
}

const AddRoleControl = ({
  orgId,
  existing,
  onAdd,
}: {
  orgId: string
  existing: RoleName[]
  onAdd: (role: RoleName) => void
}) => {
  const { data } = useQuery({
    ...listAssignableRolesOrganisationsOrgIdAssignableRolesGetOptions({
      path: { org_id: orgId },
    }),
  })
  const available = (data?.roles ?? []).filter((r) => !existing.includes(r))
  const [role, setRole] = useState<RoleName | ''>('')

  if (available.length === 0) return null

  return (
    <div className="govuk-!-margin-top-2 flex gap-2">
      <label className="govuk-visually-hidden" htmlFor="add-role-select">
        Add role
      </label>
      <select
        id="add-role-select"
        className="govuk-select"
        value={role}
        onChange={(e) => setRole(e.target.value as RoleName | '')}
      >
        <option value="">Add role...</option>
        {available.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>
      <button
        type="button"
        className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0"
        disabled={!role}
        onClick={() => {
          if (role) {
            onAdd(role)
            setRole('')
          }
        }}
      >
        Add
      </button>
    </div>
  )
}
