'use client'

import { useAuthz } from '@/hooks/use-authz'
import type { Permission } from '@/lib/client/types.gen'

/**
 * A `<select>` of the orgs the caller is an active member of.
 *
 * Orgs where the caller lacks `requirePermission` are shown but disabled
 * (greyed out) so the user understands they're a member but can't act there,
 * rather than silently omitting them. Selection is cosmetic gating only - the
 * backend independently enforces the action on submit.
 */
export function OrgSelect({
  id = 'org-select',
  value,
  onChange,
  requirePermission,
  includePersonal = true,
  personalLabel = 'Personal (no organisation)',
}: {
  id?: string
  value: string
  onChange: (orgId: string) => void
  requirePermission?: Permission
  includePersonal?: boolean
  personalLabel?: string
}) {
  const { orgs, can, isLoading } = useAuthz()

  return (
    <select
      id={id}
      className="govuk-select"
      value={value}
      disabled={isLoading}
      onChange={(e) => onChange(e.target.value)}
    >
      {includePersonal && <option value="">{personalLabel}</option>}
      {(orgs ?? []).map((org) => {
        const allowed =
          requirePermission === undefined || can(requirePermission, org.id)
        return (
          <option key={org.id} value={org.id} disabled={!allowed}>
            {org.name}
            {allowed ? '' : ' (no permission)'}
          </option>
        )
      })}
    </select>
  )
}
