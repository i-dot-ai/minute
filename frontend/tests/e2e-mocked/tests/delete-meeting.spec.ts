import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { routeDeleteTranscription } from '@/tests/e2e-mocked/utilities/routes/transcription'
import { transcriptions } from '@/tests/e2e-mocked/mocked-responses/transcriptions'
import { test, expect } from '@playwright/test'

test('deleting a meeting removes it from the transcriptions list', async ({
  page,
}) => {
  await mockBackend(page)
  await routeDeleteTranscription(page, { transcriptions })

  await page.goto('/')
  await page.getByRole('link', { name: 'transcripts' }).click()
  await expect(page).toHaveURL(/\/transcriptions$/)

  const target = transcriptions.items[0]
  const row = page.getByRole('link', { name: target.title! })
  await expect(row).toBeVisible()

  const deleteRequest = page.waitForRequest(
    (req) =>
      req.method() === 'DELETE' &&
      new RegExp(`/transcriptions/${target.id}$`).test(req.url())
  )

  await page.getByRole('button', { name: `Delete ${target.title}` }).click()

  const dialog = page.getByRole('alertdialog')
  await expect(dialog).toBeVisible()
  await expect(
    dialog.getByText('Are you sure you want to delete this transcription?')
  ).toBeVisible()

  await dialog.getByRole('button', { name: 'Delete transcription' }).click()

  await deleteRequest

  await expect(page.getByRole('link', { name: target.title! })).toHaveCount(0)
  await expect(
    page.getByRole('link', { name: transcriptions.items[1].title! })
  ).toBeVisible()
})

test('cancelling the delete dialog keeps the meeting', async ({ page }) => {
  await mockBackend(page)
  let deleteFired = false
  page.on('request', (req) => {
    if (req.method() === 'DELETE' && /\/transcriptions\/[^/]+$/.test(req.url()))
      deleteFired = true
  })
  await routeDeleteTranscription(page, { transcriptions })

  await page.goto('/')
  await page.getByRole('link', { name: 'transcripts' }).click()
  await expect(page).toHaveURL(/\/transcriptions$/)

  const target = transcriptions.items[0]
  await page.getByRole('button', { name: `Delete ${target.title}` }).click()

  const dialog = page.getByRole('alertdialog')
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: 'Cancel' }).click()

  await expect(dialog).toBeHidden()
  await expect(page.getByRole('link', { name: target.title! })).toBeVisible()
  expect(deleteFired).toBe(false)
})


test('select all meetings and delete deletes all meetings and renders button which leads you back to recording more meetings', async ({
  page,
}) => {
  await mockBackend(page)
  await routeDeleteTranscription(page, { transcriptions })

  await page.goto('/')
  await page.getByRole('link', { name: 'transcripts' }).click()
  await expect(page).toHaveURL(/\/transcriptions$/)

  await expect(
    page.getByRole('link', { name: transcriptions.items[0].title! })
  ).toBeVisible()

  const count = transcriptions.items.length
  const deletes: string[] = []
  page.on('request', (req) => {
    if (req.method() === 'DELETE' && /\/transcriptions\/[^/]+$/.test(req.url()))
      deletes.push(req.url())
  })
  await page.getByRole('checkbox', { name: 'Select all' }).check()
  await expect(page.getByRole('checkbox', { name: 'Select all' })).toBeChecked()

  await page
    .getByRole('button', { name: `Delete ${count} selected` })
    .click()

  const dialog = page.getByRole('alertdialog')
  await dialog.getByRole('button', { name: `Delete ${count} selected` }).click()
  await expect.poll(() => deletes.length).toBe(count)

  for (const item of transcriptions.items) {
    await expect(page.getByRole('link', { name: item.title! })).toHaveCount(0)
  }
  await page.getByRole('link', { name: 'Start a new recording' }).click()
  await expect(page).toHaveURL('/')
})
