import { usersMe } from '@/tests/e2e-mocked/mocked-responses/users.me'
import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { json } from '@/tests/e2e-mocked/utilities/routes/general'
import { test, expect } from '@playwright/test'

test('changing the data retention period updates the transcriptions page', async ({
  page,
}) => {
  await mockBackend(page)

  await page.goto('/')
  await page.getByRole('link', { name: 'transcriptions' }).click()
  await expect(page).toHaveURL(/\/transcriptions$/)

  await expect(
    page.getByText('Transcriptions will be kept indefinitely')
  ).toBeVisible()

  await page.getByRole('link', { name: 'your account settings' }).click()

  await expect(page).toHaveURL('/profile#settings')
  await expect(
    page.getByRole('cell', { name: 'Transcriptions will be kept indefinitely' })
  ).toBeVisible()
  await page.getByRole('button', { name: 'Change data retention' }).click()

  const dialog = page.getByRole('dialog')
  await expect(
    dialog.getByRole('heading', { name: 'Data retention period' })
  ).toBeVisible()

  await dialog.getByRole('radio', { name: '7 days' }).check()
  await dialog.getByRole('button', { name: 'Save' }).click()

  await expect(dialog).toBeHidden()
  await expect(
    page.getByRole('cell', {
      name: 'Transcriptions will be deleted after 7 days',
    })
  ).toBeVisible()
  await page.getByRole('link', { name: 'transcriptions' }).click()
  await expect(
    page.getByText('Transcriptions will be deleted after 7 days')
  ).toBeVisible()
})

for (const [email, fixed] of [
  ['jane@businessandtrade.gov.uk', true],
  ['Jane@BUSINESSANDTRADE.GOV.UK', true],
  ['jane@dsit.gov.uk', false],
  ['jane@sub.businessandtrade.gov.uk', false],
  ['jane@notbusinessandtrade.gov.uk', false],
  ['jane@businessandtrade.gov.uk.example.com', false],
]) {
  test(`fixed retention applies only to the exact DBT domain: ${email}`, async ({
    page,
  }) => {
    await mockBackend(page)
    await page.route('**/api/proxy/users/me', (route) =>
      route.fulfill(json(200, { ...usersMe, email, data_retention_days: 30 }))
    )

    await page.goto('/profile#settings')
    await expect(
      page.getByRole('cell', {
        name: 'Transcriptions will be deleted after 30 days',
      })
    ).toBeVisible()

    await expect(
      page.getByRole('button', { name: 'Change data retention', exact: true })
    ).toHaveCount(fixed ? 0 : 1)
    await expect(
      page.getByText(
        'This has been set by your department and cannot be changed'
      )
    ).toHaveCount(fixed ? 1 : 0)
  })
}
