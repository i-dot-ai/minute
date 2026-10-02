import { expect, type Page } from '@playwright/test'

export const goToSummaryPage = async (page: Page, meetingTitle: string) => {
  await page.goto('/')
  await page.getByRole('link', { name: 'transcripts' }).click()
  await expect(page).toHaveURL(/\/transcriptions$/)

  await page.getByRole('link', { name: meetingTitle }).first().click()

  await expect(page).toHaveURL(/\/transcriptions\/[^/]+\/summary\/[^/]+$/)
  await expect(
    page.getByRole('heading', { level: 1, name: meetingTitle })
  ).toBeVisible()
}

export const enterEditMode = async (page: Page) => {
  await page.getByRole('button', { name: 'Edit', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()
}
