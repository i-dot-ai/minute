import type { Page } from '@playwright/test'

export type StaticMock = {
  method: string
  path: string
  status: number
  response: unknown
}
// Use urls that mimic prod set up to catch CSP action properly
export const UPLOAD_URL =
  'https://i-dot-ai-test-minute-data.s3.eu-west-2.amazonaws.com/upload'

export const STORAGE_HOST =
  'https://i-dot-ai-test-minute-data.s3.eu-west-2.amazonaws.com'

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

export function json(status: number, body: unknown) {
  return {
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  }
}

export async function routeStorage(page: Page): Promise<void> {
  await page.route(`${UPLOAD_URL}**`, (route) =>
    route.fulfill({ status: 200, body: '' })
  )

  await page.route(`${STORAGE_HOST}/**`, (route) =>
    route.fulfill({ status: 200, contentType: 'audio/mpeg', body: '' })
  )
}
