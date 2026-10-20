import type { Page } from '@playwright/test'
import type {
  MinuteListItem,
  MinuteVersionResponse,
} from '@/lib/client/types.gen'
import { json } from './general'

const CREATED_MINUTE_PREFIX = 'created-minute-'

/**
 * Stateful minute (summary) routes: list, create and delete.
 *
 * Register AFTER mockBackend(page) so these take precedence over the static
 * routes (Playwright matches the most recently registered route first). The
 * handlers mutate a local copy of the list so creates and deletes are
 * reflected when the UI invalidates and refetches.
 *
 * A newly created minute is served with a still-generating version so the
 * summary page shows the "Generating summary" state, matching the real flow.
 */
export async function routeMinutes(
  page: Page,
  {
    transcriptionId,
    minutes,
  }: {
    transcriptionId: string
    minutes: MinuteListItem[]
  }
): Promise<void> {
  const remaining = [...minutes]

  await page.route('**/api/proxy/minutes/*/versions', (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    const { pathname } = new URL(route.request().url())
    const minuteId = pathname.split('/').at(-2)
    if (!minuteId?.startsWith(CREATED_MINUTE_PREFIX)) return route.fallback()
    const now = new Date().toISOString()
    const generating: MinuteVersionResponse = {
      id: `${minuteId}-version-0`,
      minute_id: minuteId,
      status: 'in_progress',
      created_datetime: now,
      updated_datetime: now,
      html_content: '',
      error: null,
      ai_edit_instructions: null,
      content_source: 'initial_generation',
    }
    return route.fulfill(json(200, [generating]))
  })

  await page.route('**/api/proxy/minutes/*', (route) => {
    if (route.request().method() !== 'DELETE') return route.fallback()
    const minuteId = new URL(route.request().url()).pathname.split('/').at(-1)
    const index = remaining.findIndex((minute) => minute.id === minuteId)
    if (index !== -1) remaining.splice(index, 1)
    return route.fulfill(json(200, {}))
  })

  await page.route(
    `**/api/proxy/transcription/${transcriptionId}/minutes`,
    (route) => {
      const method = route.request().method()

      if (method === 'GET') return route.fulfill(json(200, remaining))

      if (method === 'POST') {
        const body = route.request().postDataJSON() as {
          template_name: string
          agenda?: string | null
        }
        const now = new Date().toISOString()
        const created: MinuteListItem = {
          id: `${CREATED_MINUTE_PREFIX}${remaining.length}`,
          created_datetime: now,
          updated_datetime: now,
          transcription_id: transcriptionId,
          template_name: body.template_name,
          agenda: body.agenda ?? null,
        }
        remaining.unshift(created)
        return route.fulfill(json(200, created))
      }

      return route.fallback()
    }
  )
}
