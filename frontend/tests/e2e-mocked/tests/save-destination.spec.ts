import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { json } from '@/tests/e2e-mocked/utilities/routes/general'
import { test, expect, type Page } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type {
  MyOrgsResponse,
  MyPermissionsResponse,
} from '@/lib/client/types.gen'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const sampleMeeting = path.resolve(
  __dirname,
  '../../fixtures/sample-meeting.mp3'
)

const ORG_ID = '11111111-1111-1111-1111-111111111111'

async function mockAuthz(page: Page, orgs: MyOrgsResponse['orgs']) {
  await page.route('**/api/proxy/users/me/permissions', (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill(
      json(200, { permissions: [] } satisfies MyPermissionsResponse)
    )
  })
  await page.route('**/api/proxy/users/me/organisations', (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill(json(200, { orgs } satisfies MyOrgsResponse))
  })
}

async function captureRecordingBody(page: Page): Promise<() => unknown> {
  let body: unknown
  await page.route('**/api/proxy/recordings', (route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    body = route.request().postDataJSON()
    return route.fulfill(
      json(200, {
        id: 'meeting-1-recording',
        upload_url:
          'https://i-dot-ai-test-minute-data.s3.eu-west-2.amazonaws.com/upload',
      })
    )
  })
  return () => body
}

test.beforeEach(async ({ page }) => {
  await mockBackend(page)
})

test('no dropdown when the user is in no organisations', async ({ page }) => {
  await mockAuthz(page, [])

  await page.goto('/')
  await page.getByRole('radio', { name: 'Upload a file' }).check()
  await page
    .locator('input[type="file"][name="file"]')
    .setInputFiles(sampleMeeting)
  await page.getByRole('button', { name: 'Upload file' }).click()

  await expect(page.getByLabel('Save to:')).toHaveCount(0)
})

test('stamps the chosen org_id on the recording', async ({ page }) => {
  await mockAuthz(page, [
    {
      id: ORG_ID,
      name: 'Cabinet Office',
      is_active: true,
      roles: ['member'],
      my_permissions: ['file.create'],
    },
  ])
  const getBody = await captureRecordingBody(page)

  await page.goto('/')
  await page.getByRole('radio', { name: 'Upload a file' }).check()
  await page
    .locator('input[type="file"][name="file"]')
    .setInputFiles(sampleMeeting)
  await page.getByRole('button', { name: 'Upload file' }).click()

  const destination = page.getByLabel('Save to:')
  await expect(destination).toBeVisible()
  await destination.selectOption(ORG_ID)

  await page.getByRole('button', { name: 'Generate summary' }).click()

  await expect(page).toHaveURL(/\/new\/status\/[^/]+$/, { timeout: 10_000 })
  expect(getBody()).toMatchObject({ org_id: ORG_ID })
})

test('personal selection sends no org_id', async ({ page }) => {
  await mockAuthz(page, [
    {
      id: ORG_ID,
      name: 'Cabinet Office',
      is_active: true,
      roles: ['member'],
      my_permissions: ['file.create'],
    },
  ])
  const getBody = await captureRecordingBody(page)

  await page.goto('/')
  await page.getByRole('radio', { name: 'Upload a file' }).check()
  await page
    .locator('input[type="file"][name="file"]')
    .setInputFiles(sampleMeeting)
  await page.getByRole('button', { name: 'Upload file' }).click()

  await expect(page.getByLabel('Save to:')).toBeVisible()
  await page.getByRole('button', { name: 'Generate summary' }).click()

  await expect(page).toHaveURL(/\/new\/status\/[^/]+$/, { timeout: 10_000 })
  const body = getBody() as { org_id?: string | null }
  expect(body.org_id ?? null).toBeNull()
})
