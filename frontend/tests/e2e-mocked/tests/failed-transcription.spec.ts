import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { routeFailedTranscription } from '@/tests/e2e-mocked/utilities/routes/transcription'
import { meeting1 } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-1'
import { meeting1Recordings } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-1.recordings'
import { test, expect } from '@playwright/test'

test('a failed transcription shows the internal error message and retry', async ({
  page,
}) => {
  await mockBackend(page)
  await routeFailedTranscription(page, {
    transcription: meeting1,
    error: 'Something exploded',
    recordings: meeting1Recordings,
  })

  await page.goto(`/transcriptions/${meeting1.id}`)

  await expect(
    page.getByRole('heading', { name: meeting1.title! })
  ).toBeVisible()
  await expect(
    page.getByText('There was an internal server error.')
  ).toBeVisible()
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible()
})

test('a no-audio failure shows the no usable audio message', async ({
  page,
}) => {
  await mockBackend(page)
  await routeFailedTranscription(page, {
    transcription: meeting1,
    error: 'No transcription phrases found in the audio',
    recordings: meeting1Recordings,
  })

  await page.goto(`/transcriptions/${meeting1.id}`)

  await expect(
    page.getByText('No usable audio detected.')
  ).toBeVisible()
})

test('a legacy failed transcription with no recording shows the empty meeting page', async ({
  page,
}) => {
  await mockBackend(page)
  await routeFailedTranscription(page, {
    transcription: meeting1,
    error: 'Something exploded',
    recordings: [],
  })

  await page.goto(`/transcriptions/${meeting1.id}`)

  await expect(
    page.getByRole('heading', { name: 'Empty meeting' })
  ).toBeVisible()
  await expect(page.getByRole('button', { name: 'Try again' })).toHaveCount(0)
})

test('retrying a failed transcription reuses the same job and goes to status', async ({
  page,
}) => {
  await mockBackend(page)
  await routeFailedTranscription(page, {
    transcription: meeting1,
    error: 'Something exploded',
    recordings: meeting1Recordings,
  })

  await page.goto(`/transcriptions/${meeting1.id}`)

  const retryRequest = page.waitForRequest(
    (req) =>
      req.method() === 'POST' &&
      new RegExp(`/transcriptions/${meeting1.id}/retry$`).test(req.url())
  )

  await page.getByRole('button', { name: 'Try again' }).click()

  const dialog = page.getByRole('dialog')
  await expect(
    dialog.getByRole('heading', { name: 'Generate summary' })
  ).toBeVisible()
  await dialog.getByRole('button', { name: 'Generate summary' }).click()

  await retryRequest
  await expect(page).toHaveURL(new RegExp(`/new/status/${meeting1.id}$`))
})
