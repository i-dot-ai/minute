import { test, expect } from '@playwright/test'
import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { PAGES_TO_TEST } from '@/tests/e2e-mocked/utilities/common'

for (const url of PAGES_TO_TEST) {
  test(`should have no CSP violations on ${url}`, async ({ page }) => {
    const violations: string[] = []
    await mockBackend(page)
    page.on('console', (msg) => {
      if (msg.text().includes('Content Security Policy')) {
        violations.push(msg.text())
      }
    })

    await page.goto(url)
    await page.getByText('Loading...').waitFor({ state: 'detached' })

    expect(violations).toEqual([])
  })
}
