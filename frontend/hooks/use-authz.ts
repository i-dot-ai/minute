'use client'

import {
  getMyOrganisationsUsersMeOrganisationsGetOptions,
  getMyPermissionsUsersMePermissionsGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import type { MyOrg, Permission } from '@/lib/client/types.gen'
import { useQuery } from '@tanstack/react-query'

function has(
  permissions: readonly Permission[] | undefined,
  permission: Permission
): boolean {
  return !!permissions && permissions.includes(permission)
}

/**
 * Unified authorization for the UI, across the global and per-org contexts.
 */
export function useAuthz() {
  const permissionsQuery = useQuery({
    ...getMyPermissionsUsersMePermissionsGetOptions(),
  })
  const orgsQuery = useQuery({
    ...getMyOrganisationsUsersMeOrganisationsGetOptions(),
  })

  const permissions = permissionsQuery.data?.permissions
  const orgs: MyOrg[] | undefined = orgsQuery.data?.orgs

  return {
    /** Global-scope permissions. */
    permissions,
    /** Org-scope permissions. */
    orgs,
    isLoading: permissionsQuery.isLoading || orgsQuery.isLoading,
    can: (permission: Permission, orgId?: string) =>
      orgId === undefined
        ? has(permissions, permission)
        : has(orgs?.find((o) => o.id === orgId)?.my_permissions, permission),
  }
}
