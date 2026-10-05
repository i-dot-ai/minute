import type { Page } from '@playwright/test'
import type { TemplateMetadata, TemplateResponse } from '@/lib/client/types.gen'
import { templates } from '../../mocked-responses/templates'
import { userTemplates } from '../../mocked-responses/user-templates'
import { usersMe } from '../../mocked-responses/users.me'
import { json } from './general'

export async function routeTemplates(page: Page): Promise<void> {
  const systemTemplates: TemplateMetadata[] = structuredClone(templates)
  const userTemplatesState: TemplateResponse[] = structuredClone(userTemplates)

  await page.route('**/api/proxy/templates', (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill(json(200, systemTemplates))
  })

  await page.route('**/api/proxy/user-templates', (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill(json(200, userTemplatesState))
  })

  await page.route('**/api/proxy/user-templates/*', (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    const { pathname } = new URL(route.request().url())
    const id = pathname.split('/').at(-1)
    const found = userTemplatesState.find((template) => template.id === id)
    if (!found) return route.fallback()
    return route.fulfill(json(200, found))
  })

  await page.route('**/api/proxy/users/default-template', (route) => {
    if (route.request().method() !== 'PATCH') return route.fallback()
    const body = route.request().postDataJSON() as {
      template_id?: string | null
      template_name?: string | null
    }
    for (const template of userTemplatesState)
      template.is_default = template.id === body.template_id
    for (const template of systemTemplates)
      template.is_default = template.name === body.template_name
    return route.fulfill(json(200, usersMe))
  })
}
