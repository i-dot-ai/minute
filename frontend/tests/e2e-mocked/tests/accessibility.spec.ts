import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { meeting1 } from '../mocked-responses/mock-meeting-1'
import { meeting1Minutes } from '../mocked-responses/mock-meeting-1.minutes'
import { meeting1Versions } from '../mocked-responses/mock-meeting-1.versions'
import { templates } from '../mocked-responses/templates'
import { userTemplates } from '../mocked-responses/user-templates'
import { mockBackend } from '@/tests/e2e-mocked/utilities/mock-backend'

test.beforeEach(async ({ page }) => {
  await mockBackend(page)
})
const PAGES_TO_TEST = [
  '/',
  `/new/status/${meeting1.id}`,
  `/transcriptions/${meeting1.id}/summary/${meeting1Minutes[0].id}?version=${meeting1Versions[0].id}`,
  `/transcriptions/${meeting1.id}/transcript`,
  '/templates',
  '/templates/create',
  '/templates/create?/templates/create?example=my-general',
  `/templates/system/${templates[0].name}`,
  `/templates/${userTemplates[0].id}`,
  '/support',
  '/privacy',
  '/unauthorised',
]

const PAGES_WITH_EDIT_MODE = [
  `/transcriptions/${meeting1.id}/summary/${meeting1Minutes[0].id}?version=${meeting1Versions[0].id}`,
  `/transcriptions/${meeting1.id}/transcript`,
  `/templates/${userTemplates[0].id}`,
]

for (const url of PAGES_TO_TEST) {
  test(`should have no accessibility violations on ${url}`, async ({
    page,
  }) => {
    await page.goto(url)

    await page.getByText('Loading...').waitFor({ state: 'detached' })

    const accessibilityScanResults = await new AxeBuilder({ page }).analyze()
    expect(accessibilityScanResults.violations).toEqual([])
  })
}

for (const url of PAGES_WITH_EDIT_MODE) {
  test(`should have no accessibility violations on ${url} in edit mode`, async ({
    page,
  }) => {
    await page.goto(url)

    await page.getByText('Loading...').waitFor({ state: 'detached' })

    await page.getByRole('button', { name: 'Edit' }).click()

    const accessibilityScanResults = await new AxeBuilder({ page }).analyze()
    expect(accessibilityScanResults.violations).toEqual([])
  })
}
