import type { Page } from '@playwright/test'
import { json } from './http'

export type StaticMock = {
  method: string
  path: string
  status: number
  response: unknown
}

export async function routeStatic(
  page: Page,
  mocks: StaticMock[]
): Promise<void> {
  for (const mock of mocks) {
    await page.route(`**/api/proxy${mock.path}**`, (route) => {
      const { pathname } = new URL(route.request().url())
      if (pathname !== `/api/proxy${mock.path}`) return route.fallback()
      if (route.request().method() !== mock.method) return route.fallback()
      return route.fulfill(json(mock.status, mock.response))
    })
  }
}
