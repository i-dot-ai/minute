import type { Page } from '@playwright/test'
import type {
  MinuteListItem,
  TranscriptionGetResponse,
} from '@/lib/client/types.gen'
import { json } from './http'

export async function routeTranscription(
  page: Page,
  {
    transcription,
    minutes,
  }: {
    transcription: TranscriptionGetResponse
    minutes: MinuteListItem[]
  }
): Promise<void> {
  const transcriptionId = transcription.id

  await page.route(`**/api/proxy/transcriptions/${transcriptionId}`, (route) => {
    if (route.request().method() !== 'PATCH') return route.fallback()
    const body = route.request().postDataJSON() as Partial<TranscriptionGetResponse>
    Object.assign(transcription, body)
    return route.fulfill(json(200, transcription))
  })

  await page.route(
    `**/api/proxy/transcription/${transcriptionId}/minutes`,
    (route) => {
      if (route.request().method() !== 'POST') return route.fallback()
      return route.fulfill(json(200, minutes[0]))
    }
  )
}
