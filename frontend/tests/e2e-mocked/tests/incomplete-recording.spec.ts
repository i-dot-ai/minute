import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { test, expect, type Page } from '@playwright/test'

const seedOfflineRecording = async (page: Page) => {
  await mockBackend(page)
  await page.goto('/transcriptions')
  await page.evaluate(() => {
    return new Promise<void>((resolve, reject) => {
      const open = indexedDB.open('MinuteDB', 1)
      open.onupgradeneeded = () =>
        open.result.createObjectStore('recordings', {
          keyPath: 'recording_id',
        })
      open.onsuccess = () => {
        const db = open.result
        const tx = db.transaction('recordings', 'readwrite')
        tx.objectStore('recordings').add({
          recording_id: 'seeded-recording-1',
          blob: new Blob(['fake-audio'], { type: 'audio/webm' }),
          updated_at: new Date(),
        })
        tx.oncomplete = () => resolve()
        tx.onerror = () => reject(tx.error)
      }
      open.onerror = () => reject(open.error)
    })
  })
  await page.reload()
}

test('an incomplete recording can be deleted', async ({ page }) => {
  await seedOfflineRecording(page)

  const deleteButton = page.getByRole('button', {
    name: /^Delete incomplete recording/,
  })
  await expect(deleteButton).toBeVisible()
  await expect(page.getByText('Not uploaded').first()).toBeVisible()

  await deleteButton.click()

  const dialog = page.getByRole('alertdialog')
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: 'Discard recording' }).click()

  await expect(
    page.getByRole('button', { name: /^Delete incomplete recording/ })
  ).toHaveCount(0)
})

test('an incomplete recording can be uploaded and starts transcription', async ({
  page,
}) => {
  await seedOfflineRecording(page)

  const uploadButton = page.getByRole('button', {
    name: /^Upload incomplete recording/,
  })
  await expect(uploadButton).toBeVisible()

  const createTranscription = page.waitForRequest(
    (req) =>
      req.method() === 'POST' &&
      /\/api\/proxy\/transcriptions$/.test(req.url())
  )

  await uploadButton.click()

  const dialog = page.getByRole('dialog')
  await expect(
    dialog.getByRole('heading', { name: 'Generate summary' })
  ).toBeVisible()
  await dialog.getByRole('button', { name: 'Generate summary' }).click()

  await createTranscription
  await expect(page).toHaveURL(/\/new\/status\/[0-9a-f-]+$/)
})
