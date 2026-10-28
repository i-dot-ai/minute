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
    page.getByRole('heading', { name: meeting1.title!, level: 1 })
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

  await expect(page.getByText('No usable audio detected.')).toBeVisible()
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
  await expect(dialog.getByLabel('Choose a language')).toHaveValue('en')
  await dialog.getByLabel('Choose a language').selectOption('cy')
  await dialog.getByLabel('Choose a template:').selectOption('default:Cabinet')
  await dialog
    .getByRole('button', { name: 'Set Cabinet as default template' })
    .click()
  await expect(
    dialog.getByRole('option', { name: 'Cabinet (Default)', exact: true })
  ).toHaveCount(1)
  await expect(dialog.getByLabel('Choose a language')).toHaveValue('cy')
  await dialog.getByRole('button', { name: 'Generate summary' }).click()

  expect((await retryRequest).postDataJSON().language).toBe('cy')
  await expect(page).toHaveURL(new RegExp(`/new/status/${meeting1.id}$`))
})

for (const [status, detail] of [
  [
    409,
    'The previous transcription is still finishing; please try again shortly',
  ],
  [503, 'Could not check transcription workflow; please try again'],
  [503, undefined],
] as const) {
  test(`a rejected retry shows an error and can be retried (${status}, ${detail ?? 'fallback'})`, async ({
    page,
  }) => {
    await mockBackend(page)
    await routeFailedTranscription(page, {
      transcription: meeting1,
      error: 'Something exploded',
      recordings: meeting1Recordings,
    })
    const retryUrl = `**/api/proxy/transcriptions/${meeting1.id}/retry`
    await page.route(retryUrl, (route) =>
      route.fulfill({ status, json: { detail } })
    )
    await page.goto(`/transcriptions/${meeting1.id}`)
    await page.getByRole('button', { name: 'Try again' }).click()
    const dialog = page.getByRole('dialog')
    await dialog.getByRole('button', { name: 'Generate summary' }).click()
    await expect(dialog.getByRole('alert')).toHaveText(
      detail ?? 'Could not restart the transcription. Please try again.'
    )
    await expect(page).toHaveURL(new RegExp(`/transcriptions/${meeting1.id}$`))
    await expect(
      dialog.getByRole('button', { name: 'Generate summary' })
    ).toBeEnabled()
    await dialog.getByRole('button', { name: 'Cancel' }).click()
    await page.getByRole('button', { name: 'Try again' }).click()
    await expect(dialog.getByRole('alert')).toHaveCount(0)
    await page.unroute(retryUrl)
    await page.route(retryUrl, (route) =>
      route.fulfill({ status: 201, json: { id: meeting1.id } })
    )
    await dialog.getByRole('button', { name: 'Generate summary' }).click()
    await expect(page).toHaveURL(new RegExp(`/new/status/${meeting1.id}$`))
  })
}
