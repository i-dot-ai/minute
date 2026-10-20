import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { goToSummaryPage } from '@/tests/e2e-mocked/utilities/navigation'
import { meeting1 } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-1'
import { meeting2 } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-2'
import { meeting2Minutes } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-2.minutes'
import { test, expect } from '@playwright/test'

test('switching version history shows the selected version', async ({
  page,
}) => {
  await mockBackend(page)
  await goToSummaryPage(page, meeting1.title!)

  await page.getByRole('button', { name: 'Edit', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()

  const editor = page.getByRole('textbox', { name: 'Summary editor' })
  await expect(editor).toContainText("it's changed now and update twice")

  await page.getByLabel('Version history').selectOption({ index: 2 })

  await expect(editor).toContainText("it's changed now and agian")
  await expect(editor).not.toContainText("it's changed now and update twice")
})

test('switching between summaries navigates to the selected one', async ({
  page,
}) => {
  await mockBackend(page, 'meeting-2')
  await goToSummaryPage(page, meeting2.title!)

  const nav = page.getByRole('navigation', { name: 'Summaries and transcript' })
  const executive = meeting2Minutes.find(
    (minute) => minute.template_name === 'Executive summary'
  )!

  await nav.getByRole('link', { name: 'Executive summary' }).first().click()

  await expect(page).toHaveURL(
    new RegExp(`/transcriptions/[^/]+/summary/${executive.id}$`)
  )

  await expect(
    nav.getByRole('link', { name: 'Executive summary' }).first()
  ).toHaveAttribute('aria-current', 'page')
})
