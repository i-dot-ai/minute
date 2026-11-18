import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'
import { test, expect, type Page } from '@playwright/test'

const TICKETS_URL = '**/api/proxy/support/tickets'

async function goToSupportPage(page: Page) {
  await page.goto('/')
  await page.getByRole('link', { name: 'Contact' }).click()
  await expect(page).toHaveURL(/\/support$/)
}

test('sending a message shows the ticket reference', async ({ page }) => {
  await mockBackend(page)
  await page.route(TICKETS_URL, (route) =>
    route.fulfill({ status: 200, json: { reference: 'MIN-123' } })
  )
  await goToSupportPage(page)

  const ticketRequest = page.waitForRequest(
    (req) => req.method() === 'POST' && /\/support\/tickets$/.test(req.url())
  )

  await page
    .getByLabel('What is your message about?')
    .selectOption({ label: 'I have a recommendation' })
  await page
    .getByLabel('Message', { exact: true })
    .fill('Please add a dark mode')
  await page.getByRole('button', { name: 'Send message' }).click()

  expect((await ticketRequest).postDataJSON()).toEqual({
    category: 'recommendation',
    message: 'Please add a dark mode',
  })
  await expect(
    page.getByRole('heading', { name: 'Message sent' })
  ).toBeVisible()
  await expect(page.getByText('MIN-123')).toBeVisible()
})

test('the category defaults to issue', async ({ page }) => {
  await mockBackend(page)
  await goToSupportPage(page)

  await expect(page.getByLabel('What is your message about?')).toHaveValue(
    'issue'
  )
})

for (const message of ['', '   ']) {
  test(`an empty message (${JSON.stringify(message)}) shows an error and is not sent`, async ({
    page,
  }) => {
    await mockBackend(page)
    let ticketSent = false
    await page.route(TICKETS_URL, (route) => {
      ticketSent = true
      return route.fulfill({ status: 200, json: { reference: 'MIN-1' } })
    })
    await goToSupportPage(page)

    await page.getByLabel('Message', { exact: true }).fill(message)
    await page.getByRole('button', { name: 'Send message' }).click()

    await expect(
      page.getByRole('heading', { name: 'There is a problem' })
    ).toBeVisible()
    await expect(
      page.getByRole('link', { name: 'Enter a message' })
    ).toBeVisible()
    expect(ticketSent).toBe(false)
  })
}

for (const status of [502, 503]) {
  test(`a ${status} from the backend shows the email fallback`, async ({
    page,
  }) => {
    await mockBackend(page)
    await page.route(TICKETS_URL, (route) =>
      route.fulfill({ status, json: { detail: 'Failed' } })
    )
    await goToSupportPage(page)

    await page
      .getByLabel('Message', { exact: true })
      .fill('Upload keeps failing')
    await page.getByRole('button', { name: 'Send message' }).click()

    const alert = page.getByRole('alert')
    await expect(
      alert.getByText('Your message could not be sent')
    ).toBeVisible()
    await expect(
      alert.getByRole('link', { name: 'minute-support@dsit.gov.uk' })
    ).toBeVisible()
    await expect(
      page.getByRole('button', { name: 'Send message' })
    ).toBeVisible()
  })
}

test('the form is hidden when the user cannot be loaded', async ({ page }) => {
  await mockBackend(page)
  await page.route('**/api/proxy/users/me', (route) =>
    route.fulfill({ status: 401, json: { detail: 'Not authenticated' } })
  )
  await page.goto('/support')

  await expect(page.getByRole('heading', { name: 'Contact us' })).toBeVisible()
  await expect(
    page.getByRole('link', { name: 'minute-support@dsit.gov.uk' })
  ).toBeVisible()
  await expect(page.getByRole('button', { name: 'Send message' })).toHaveCount(
    0
  )
})
