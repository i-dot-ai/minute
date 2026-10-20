import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { routeMinutes } from '@/tests/e2e-mocked/utilities/routes/minutes'
import { goToSummaryPage } from '@/tests/e2e-mocked/utilities/navigation'
import { meeting1 } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-1'
import { meeting1Minutes } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-1.minutes'
import { meeting2 } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-2'
import { meeting2Minutes } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-2.minutes'
import { test, expect } from '@playwright/test'

test('deleting one of several summaries removes it and keeps the rest', async ({
  page,
}) => {
  await mockBackend(page, 'meeting-2')
  await routeMinutes(page, {
    transcriptionId: meeting2.id,
    minutes: meeting2Minutes,
  })

  await goToSummaryPage(page, meeting2.title!)

  const summaryToDelete = meeting2Minutes[0]

  const deleteRequest = page.waitForRequest(
    (req) =>
      req.method() === 'DELETE' &&
      new RegExp(`/minutes/${summaryToDelete.id}$`).test(req.url())
  )

  await page.getByRole('button', { name: 'Delete summary' }).click()

  const dialog = page.getByRole('alertdialog')
  await expect(dialog).toBeVisible()
  await expect(dialog.getByText('Delete this summary?')).toBeVisible()

  await dialog.getByRole('button', { name: 'Delete summary' }).click()

  await deleteRequest

  // After delete the user is sent to the transcription, which redirects to the
  // remaining first summary. The deleted one is gone from the summaries nav.
  await expect(page).toHaveURL(/\/transcriptions\/[^/]+\/summary\/[^/]+$/)

  const nav = page.getByRole('navigation', { name: 'Summaries and transcript' })
  await expect(
    nav.getByRole('link', { name: 'Executive summary' })
  ).toBeVisible()
})

test('deleting the only summary leaves the meeting with no summary and option to make a new one', async ({
  page,
}) => {
  await mockBackend(page, 'meeting-1')
  await routeMinutes(page, {
    transcriptionId: meeting1.id,
    minutes: meeting1Minutes,
  })

  await goToSummaryPage(page, meeting1.title!)

  await page.getByRole('button', { name: 'Delete summary' }).click()

  const dialog = page.getByRole('alertdialog')
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: 'Delete summary' }).click()

  await expect(page).toHaveURL(/\/transcriptions\/[^/]+\/transcript$/)

  await page.getByRole('link', { name: 'Summary', exact: true }).click()

  await expect(page).toHaveURL(/\/transcriptions\/[^/]+\/summary$/)

  await expect(page.getByText('No summary generated')).toBeVisible()

  const createNewSummaryButton = page.getByRole('button', {
    name: 'New summary',
  })

  await expect(createNewSummaryButton).toBeVisible()

  await createNewSummaryButton.click()

  await page.getByRole('button', { name: 'Generate summary' }).click()

  await expect(page.getByText('Generating summary')).toBeVisible()
})
