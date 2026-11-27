import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { usersMe } from '@/tests/e2e-mocked/mocked-responses/users.me'
import {
  recordAudioFlow,
  statusToSummaryFlow,
  uploadAudioFlow,
} from '@/tests/e2e-mocked/utilities/navigation'
import { test, expect } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const sampleMeeting = path.resolve(
  __dirname,
  '../../fixtures/sample-meeting.mp3'
)

test.beforeEach(async ({ page }) => {
  await mockBackend(page)
  // getDisplayMedia isn't covered by the fake-media flags and may reject in CI.
  await page.addInitScript(() => {
    navigator.mediaDevices.getDisplayMedia = async () => {
      ;(
        window as unknown as { __getDisplayMediaCalled?: boolean }
      ).__getDisplayMediaCalled = true
      return navigator.mediaDevices.getUserMedia({ audio: true })
    }
  })
})

test('In person meeting to summary', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('radio', { name: 'In person' }).check()

  await expect(page.getByLabel('Select microphone:')).toBeEnabled()
  await expect(
    page.getByRole('option', { name: 'Requesting microphone access...' })
  ).toHaveCount(0)

  await page.getByRole('button', { name: 'Start recording' }).click()

  await recordAudioFlow(page)
  await statusToSummaryFlow(page)
})

test('Virtual meeting to summary', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('radio', { name: 'Virtual meeting' }).check()

  await expect(
    page.getByRole('heading', { name: 'Before you start' })
  ).toBeVisible()

  await expect(page.getByLabel('Select microphone:')).toBeEnabled()
  await expect(
    page.getByRole('option', { name: 'Requesting microphone access...' })
  ).toHaveCount(0)

  await page.getByRole('button', { name: 'Start recording' }).click()

  // check that screen capture was requested, since getDisplayMedia is stubbed to always succeed
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (window as unknown as { __getDisplayMediaCalled?: boolean })
            .__getDisplayMediaCalled === true
      )
    )
    .toBe(true)

  await recordAudioFlow(page)
  await statusToSummaryFlow(page)
})

test('Upload a file to summary', async ({ page }) => {
  await page.goto('/')

  await page.getByRole('radio', { name: 'Upload a file' }).check()

  await page
    .locator('input[type="file"][name="file"]')
    .setInputFiles(sampleMeeting)

  await page.getByRole('button', { name: 'Upload file' }).click()
  await page.getByRole('button', { name: 'Generate summary' }).click()

  await statusToSummaryFlow(page)
})

test('select a microphone passes device id as an exact match to prevent slipping to default audio bug', async ({
  page,
}) => {
  await page.addInitScript(() => {
    const md = navigator.mediaDevices
    md.enumerateDevices = async () =>
      [
        {
          deviceId: 'default',
          kind: 'audioinput',
          label: 'AirPods Pro',
          groupId: 'fake',
        },
        {
          deviceId: 'mac-mic',
          kind: 'audioinput',
          label: 'MacBook Pro Microphone',
          groupId: 'fake',
        },
      ] as unknown as MediaDeviceInfo[]
    const origGetUserMedia = md.getUserMedia.bind(md)
    md.getUserMedia = async (constraints) => {
      ;(
        window as unknown as { __micConstraints?: MediaStreamConstraints }
      ).__micConstraints = constraints
      return origGetUserMedia(constraints)
    }
  })

  await page.goto('/')
  await page.getByRole('radio', { name: 'In person' }).check()
  await page
    .getByLabel('Select microphone:')
    .selectOption({ label: 'MacBook Pro Microphone' })
  await page.getByRole('button', { name: 'Start recording' }).click()

  // Recording starts asynchronously, so poll until the recorder has actually
  // called getUserMedia.
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          !!(window as unknown as { __micConstraints?: MediaStreamConstraints })
            .__micConstraints
      )
    )
    .toBe(true)

  const constraints = await page.evaluate(
    () =>
      (window as unknown as { __micConstraints?: MediaStreamConstraints })
        .__micConstraints
  )
  const audio = constraints?.audio
  expect(typeof audio === 'object' ? audio?.deviceId : undefined).toEqual({
    exact: 'mac-mic',
  })
})

test('language radios are hidden if the Welsh language flag is not enabled', async ({
  page,
}) => {
  // mockBackend leaves PostHog unavailable, so the flag never resolves.
  await mockBackend(page)

  await uploadAudioFlow(page, sampleMeeting)
  await page.getByRole('button', { name: 'Generate summary' }).click()

  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await expect(dialog.getByText('Choose language:')).toHaveCount(0)
})

test('Welsh flag shows language radios if flag enabled', async ({ page }) => {
  await mockBackend(page)
  // mockBackend aborts all PostHog traffic, which leaves every flag off.
  // Serve a flags response with the Welsh option enabled instead.
  await page.route(/posthog\.com\/flags/, (route) =>
    route.fulfill({
      status: 200,
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        flags: {
          'welsh-language-option': {
            enabled: true,
            variant: null,
            metadata: { id: 1, payload: null, version: 1 },
          },
        },
        request_id: 'e2e',
        extras: {},
      }),
    })
  )

  await uploadAudioFlow(page, sampleMeeting)
  await page.getByRole('button', { name: 'Generate summary' }).click()

  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await expect(dialog.getByText('Choose language:')).toBeVisible()
  await expect(dialog.getByRole('radio', { name: 'Cymraeg' })).toBeChecked()
  await expect(dialog.getByRole('radio', { name: 'English' })).not.toBeChecked()
})
