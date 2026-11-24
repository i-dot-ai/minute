'use client'

import { MemberRolesDialog } from './member-roles-dialog'
import { RolePill } from './role-pill'
import {
  addOrgMemberOrganisationsOrgIdMembersPostMutation,
  listOrgMembersOrganisationsOrgIdMembersGetOptions,
  listOrgMembersOrganisationsOrgIdMembersGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import type { OrgMember, OrgMembersResponse } from '@/lib/client/types.gen'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Pencil } from 'lucide-react'
import { FormEvent, useState } from 'react'

export const OrgMembers = ({ orgId }: { orgId: string }) => {
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<OrgMember | null>(null)

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

  const submitAddMember = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = email.trim()
    if (!trimmed) {
      setError('Enter an email address')
      return
    }
    addMember({ path: { org_id: orgId }, body: { email: trimmed } })
  }

  if (isLoading) {
    return (
      <p className="govuk-body">
        <Loader2 className="animate-spin" /> Loading members
      </p>
    )
  }

  const activeMembers = (members?.members ?? []).filter((m) => m.is_active)

  const editingMember = editing
    ? (activeMembers.find((m) => m.user_id === editing.user_id) ?? null)
    : null

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
              <span className="govuk-visually-hidden">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody className="govuk-table__body">
          {activeMembers.map((member) => (
            <tr className="govuk-table__row" key={member.user_id}>
              <td className="govuk-table__cell break-all">{member.email}</td>
              <td className="govuk-table__cell">
                <div className="flex flex-wrap">
                  {member.roles.length === 0 ? (
                    <span className="govuk-body-s">No roles</span>
                  ) : (
                    member.roles.map((role) => (
                      <RolePill key={role} role={role} />
                    ))
                  )}
                </div>
              </td>
              <td className="govuk-table__cell govuk-table__cell--numeric">
                <button
                  type="button"
                  aria-label={`Edit ${member.email}`}
                  className="govuk-link govuk-link--no-visited-state inline-flex cursor-pointer items-center border-0 bg-transparent text-(--govuk-link-colour)"
                  onClick={() => setEditing(member)}
                >
                  <Pencil className="size-4" aria-hidden="true" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {editingMember && (
        <MemberRolesDialog
          open
          onOpenChange={(next) => {
            if (!next) setEditing(null)
          }}
          orgId={orgId}
          member={editingMember}
          onMutated={onMutated}
        />
      )}

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
