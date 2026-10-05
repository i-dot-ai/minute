import type { Page } from '@playwright/test'
import type {
  ContentSource,
  MinuteVersionResponse,
} from '@/lib/client/types.gen'
import { json } from './general'

export async function routeMinuteVersions(
  page: Page,
  {
    minuteId,
    versions,
    scenario,
  }: {
    minuteId: string | undefined
    versions: MinuteVersionResponse[]
    scenario: string
  }
): Promise<void> {
  await page.route('**/api/proxy/minutes/*/versions', (route) => {
    const { pathname } = new URL(route.request().url())
    const requestedMinuteId = pathname.split('/').at(-2)
    const method = route.request().method()

    if (requestedMinuteId !== minuteId) {
      if (method !== 'GET') return route.fallback()
      return route.fulfill(json(200, []))
    }

    if (method === 'GET') return route.fulfill(json(200, versions))
    if (method !== 'POST') return route.fallback()

    const body = route.request().postDataJSON() as {
      html_content?: string
      content_source: ContentSource
    }
    const now = new Date().toISOString()
    const created: MinuteVersionResponse = {
      id: `${scenario}-version-${versions.length}`,
      minute_id: minuteId!,
      status: 'completed',
      created_datetime: now,
      updated_datetime: now,
      html_content: body.html_content ?? versions[0]?.html_content ?? '',
      error: null,
      ai_edit_instructions: null,
      content_source: body.content_source,
    }
    versions.unshift(created)
    return route.fulfill(json(201, created))
  })
}
