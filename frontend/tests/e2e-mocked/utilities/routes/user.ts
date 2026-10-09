import type { Page } from '@playwright/test'
import type { GetUserResponse } from '@/lib/client/types.gen'
import { usersMe } from '../../mocked-responses/users.me'
import { json } from './general'

export async function routeUser(page: Page): Promise<void> {
  const user: GetUserResponse = structuredClone(usersMe)

  await page.route('**/api/proxy/users/data-retention', (route) => {
    if (route.request().method() !== 'PATCH') return route.fallback()
    const body = route.request().postDataJSON() as {
      data_retention_days: number | null
    }
    user.data_retention_days = body.data_retention_days
    return route.fulfill(json(200, user))
  })

  await page.route('**/api/proxy/users/me', (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill(json(200, user))
  })
}
