'use client'

import { RemovableRolePill } from './role-pill'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  addMemberRolesOrganisationsOrgIdMembersUserIdRolesPostMutation,
  listAssignableRolesOrganisationsOrgIdAssignableRolesGetOptions,
  removeMemberRoleOrganisationsOrgIdMembersUserIdRolesRoleNameDeleteMutation,
  removeOrgMemberOrganisationsOrgIdMembersUserIdDeleteMutation,
} from '@/lib/client/@tanstack/react-query.gen'
import type {
  OrgMember,
  OrgMembersResponse,
  RoleName,
} from '@/lib/client/types.gen'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'

export const MemberRolesDialog = ({
  open,
  onOpenChange,
  orgId,
  member,
  onMutated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  orgId: string
  member: OrgMember
  onMutated: (data: OrgMembersResponse) => void
}) => {
  const [error, setError] = useState<string | null>(null)
  const [roleToAdd, setRoleToAdd] = useState<RoleName | ''>('')

  const onError = (message: string) => () => setError(message)
  const onSuccess = (data: OrgMembersResponse) => {
    onMutated(data)
    setError(null)
  }

  const { data: assignable } = useQuery({
    ...listAssignableRolesOrganisationsOrgIdAssignableRolesGetOptions({
      path: { org_id: orgId },
    }),
    enabled: open,
  })

  const { mutate: addRole, isPending: addingRole } = useMutation({
    ...addMemberRolesOrganisationsOrgIdMembersUserIdRolesPostMutation(),
    onSuccess: (data) => {
      onSuccess(data)
      setRoleToAdd('')
    },
    onError: onError('Could not add role. Try again.'),
  })
  const { mutate: removeRole } = useMutation({
    ...removeMemberRoleOrganisationsOrgIdMembersUserIdRolesRoleNameDeleteMutation(),
    onSuccess,
    onError: onError('Could not remove role. They may be the last admin.'),
  })
  const { mutate: removeMember, isPending: removingMember } = useMutation({
    ...removeOrgMemberOrganisationsOrgIdMembersUserIdDeleteMutation(),
    onSuccess: (data) => {
      onMutated(data)
      onOpenChange(false)
    },
    onError: onError('Could not remove member. They may be the last admin.'),
  })

  const available = (assignable?.roles ?? []).filter(
    (r) => !member.roles.includes(r)
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogTitle className="govuk-heading-m govuk-!-margin-bottom-1 break-all">
          {member.email}
        </DialogTitle>
        <DialogDescription className="govuk-hint govuk-!-margin-bottom-2">
          Manage this member&rsquo;s roles or remove them from the organisation.
        </DialogDescription>

        {error && (
          <p className="govuk-error-message">
            <span className="govuk-visually-hidden">Error:</span> {error}
          </p>
        )}

        <h3 className="govuk-heading-s govuk-!-margin-bottom-2">Roles</h3>
        <div className="govuk-!-margin-bottom-2 flex flex-wrap">
          {member.roles.length === 0 && (
            <p className="govuk-body-s govuk-!-margin-bottom-0">No roles</p>
          )}
          {member.roles.map((role) => (
            <RemovableRolePill
              key={role}
              role={role}
              onRemove={() =>
                removeRole({
                  path: {
                    org_id: orgId,
                    user_id: member.user_id,
                    role_name: role,
                  },
                })
              }
            />
          ))}
        </div>

        {available.length > 0 && (
          <div className="flex items-end gap-2">
            <div className="govuk-form-group govuk-!-margin-bottom-0">
              <label className="govuk-label govuk-label--s" htmlFor="add-role">
                Add role
              </label>
              <select
                id="add-role"
                className="govuk-select"
                value={roleToAdd}
                onChange={(e) => setRoleToAdd(e.target.value as RoleName | '')}
              >
                <option value="">Choose a role...</option>
                {available.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="govuk-button govuk-button--secondary govuk-!-margin-bottom-0"
              disabled={!roleToAdd || addingRole}
              onClick={() => {
                if (roleToAdd) {
                  addRole({
                    path: { org_id: orgId, user_id: member.user_id },
                    body: { roles: [roleToAdd] },
                  })
                }
              }}
            >
              {addingRole && <Loader2 className="size-4 animate-spin" />}+ Add
              role
            </button>
          </div>
        )}

        <hr className="govuk-section-break govuk-section-break--visible govuk-!-margin-top-6 govuk-!-margin-bottom-4" />

        <button
          type="button"
          className="govuk-button govuk-button--warning govuk-!-margin-bottom-0"
          disabled={removingMember}
          onClick={() =>
            removeMember({ path: { org_id: orgId, user_id: member.user_id } })
          }
        >
          {removingMember && <Loader2 className="size-4 animate-spin" />}
          Remove from organisation
        </button>
      </DialogContent>
    </Dialog>
  )
}
