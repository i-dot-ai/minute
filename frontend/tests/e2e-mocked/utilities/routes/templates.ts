import type { Page } from '@playwright/test'
import type {
  CreateUserTemplateRequest,
  Question,
  TemplateMetadata,
  TemplateResponse,
} from '@/lib/client/types.gen'
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
    const method = route.request().method()

    if (method === 'GET') return route.fulfill(json(200, userTemplatesState))
    if (method !== 'POST') return route.fallback()

    const body = route.request().postDataJSON() as CreateUserTemplateRequest
    const now = new Date().toISOString()
    const questions: Question[] | null =
      body.type === 'form'
        ? (body.questions ?? [])
            .slice()
            .sort((a, b) => a.position - b.position)
            .map((question, index) => ({
              id: `user-template-question-${userTemplatesState.length}-${index}`,
              position: question.position,
              title: question.title,
              description: question.description,
            }))
        : null

    const created: TemplateResponse = {
      id: `user-template-${userTemplatesState.length}`,
      updated_datetime: now,
      name: body.name,
      content: body.content,
      description: body.description,
      type: body.type,
      questions,
      is_default: false,
    }
    userTemplatesState.unshift(created)
    return route.fulfill(json(200, created))
  })

  await page.route('**/api/proxy/user-templates/*', (route) => {
    const method = route.request().method()
    const { pathname } = new URL(route.request().url())
    const id = pathname.split('/').at(-1)
    const index = userTemplatesState.findIndex((template) => template.id === id)
    if (index === -1) return route.fallback()

    if (method === 'GET') {
      return route.fulfill(json(200, userTemplatesState[index]!))
    }
    if (method !== 'PATCH') return route.fallback()

    const body = route.request().postDataJSON() as CreateUserTemplateRequest
    const existing = userTemplatesState[index]!
    const questions: Question[] | null =
      existing.type === 'form'
        ? (body.questions ?? [])
            .slice()
            .sort((a, b) => a.position - b.position)
            .map((question, questionIndex) => ({
              id: `${existing.id}-question-${questionIndex}`,
              position: question.position,
              title: question.title,
              description: question.description,
            }))
        : null

    const updated: TemplateResponse = {
      ...existing,
      name: body.name,
      content: body.content,
      description: body.description,
      questions,
      updated_datetime: new Date().toISOString(),
    }
    userTemplatesState[index] = updated
    return route.fulfill(json(200, updated))
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
