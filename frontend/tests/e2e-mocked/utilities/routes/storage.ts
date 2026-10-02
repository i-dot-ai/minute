import type { Page } from '@playwright/test'

const UPLOAD_URL = 'https://blob.test.local/upload'

export { UPLOAD_URL }

export async function routeStorage(page: Page): Promise<void> {
  await page.route(`${UPLOAD_URL}**`, (route) =>
    route.fulfill({ status: 200, body: '' })
  )

  await page.route('**/api/proxy/mock_storage/**', (route) =>
    route.fulfill({ status: 200, contentType: 'audio/mpeg', body: '' })
  )
}
