import type { Permission } from '@/lib/client/types.gen'
import { headers } from 'next/headers'

/**
 * The caller's permissions, fetched on the server for SSR gating.
 */
export async function getServerPermissions(): Promise<Permission[]> {
  try {
    const token = (await headers()).get('x-amzn-oidc-data')
    const response = await fetch(
      `${process.env.BACKEND_HOST}/users/me/permissions`,
      {
        headers: token ? { 'x-amzn-oidc-data': token } : {},
        cache: 'no-store',
        signal: AbortSignal.timeout(10_000),
      }
    )
    if (!response.ok) {
      console.error(`Permissions request failed: ${response.status}`)
      return []
    }
    const data: { permissions?: Permission[] } = await response.json()
    return data.permissions ?? []
  } catch (error) {
    console.error('Failed to fetch server permissions', error)
    return []
  }
}
