import { meeting1 } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-1'
import { meeting1Minutes } from '@/tests/e2e-mocked/mocked-responses/mock-meeting-1.minutes'
import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { enterEditMode } from '@/tests/e2e-mocked/utilities/navigation'
import { json } from '@/tests/e2e-mocked/utilities/routes/general'
import { expect, test } from '@playwright/test'

test('edit keywords in the meeting edit form on both pages', async ({
  page,
}) => {
  await mockBackend(page)
  const topics = Array.from({ length: 30 }, (_, index) => `topic ${index + 1}`)
  let keywords = ['freedom of information', 'information governance', ...topics]
  await page.route(
    `**/api/proxy/transcriptions/${meeting1.id}/keywords`,
    (route) => {
      if (route.request().method() === 'PUT') {
        keywords = route.request().postDataJSON().keywords
      }
      return route.fulfill(json(200, { keywords }))
    }
  )

  await page.goto(
    `/transcriptions/${meeting1.id}/summary/${meeting1Minutes[0].id}`
  )
  const section = page.getByRole('region', { name: 'Keywords', exact: true })
  await expect(section.getByText('freedom of information')).toBeVisible()
  await expect(section.locator('.govuk-tag')).toHaveText(keywords.slice(0, 8))
  await section.getByRole('button', { name: 'More', exact: true }).click()
  await expect(section.locator('.govuk-tag')).toHaveText(keywords)
  await section.getByRole('button', { name: 'Less', exact: true }).click()
  await expect(section.locator('.govuk-tag')).toHaveCount(8)
  await expect(section.getByText('Keywords', { exact: true })).toBeHidden()
  await expect(page.getByRole('button', { name: 'Edit keywords' })).toBeHidden()
  await enterEditMode(page)
  await expect(page.getByRole('button', { name: /^Remove / })).toHaveCount(32)

  await page
    .getByRole('button', { name: 'Remove freedom of information' })
    .click()
  await expect(
    page.getByRole('heading', { name: 'Keywords', exact: true })
  ).toBeVisible()
  await page.getByRole('button', { name: 'Add keyword', exact: true }).click()
  const input = page.getByRole('textbox', { name: 'New keyword' })
  await expect(input).toBeFocused()
  await input.fill('records retention')
  await input.press('Enter')
  await expect(
    page.getByRole('button', { name: 'Remove records retention' })
  ).toBeVisible()
  expect(keywords).toEqual([
    'freedom of information',
    'information governance',
    ...topics,
  ])
  await page.getByRole('button', { name: 'Save', exact: true }).click()

  await section.getByRole('button', { name: 'More', exact: true }).click()
  await expect(section.getByText('records retention')).toBeVisible()
  expect(keywords).toEqual([
    'information governance',
    ...topics,
    'records retention',
  ])
  await page.getByRole('link', { name: 'Transcript', exact: true }).click()
  await expect(page).toHaveURL(/\/transcript$/)
  await expect(section.locator('.govuk-tag')).toHaveText(keywords.slice(0, 8))
  await section.getByRole('button', { name: 'More', exact: true }).click()
  await expect(section.getByText('records retention')).toBeVisible()
  await expect(section.getByText('freedom of information')).toBeHidden()

  await enterEditMode(page)
  await expect(page.getByRole('button', { name: /^Remove / })).toHaveCount(32)
  await page.getByRole('button', { name: 'Remove records retention' }).click()
  await page.getByRole('button', { name: 'Add keyword', exact: true }).click()
  await input.fill('archiving guidance')
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  await section.getByRole('button', { name: 'More', exact: true }).click()
  await expect(section.getByText('archiving guidance')).toBeVisible()
  expect(keywords).toEqual([
    'information governance',
    ...topics,
    'archiving guidance',
  ])

  await enterEditMode(page)
  await page.getByRole('button', { name: 'Remove archiving guidance' }).click()
  await page.getByRole('button', { name: 'Discard', exact: true }).click()
  await section.getByRole('button', { name: 'More', exact: true }).click()
  await expect(section.getByText('archiving guidance')).toBeVisible()
})
