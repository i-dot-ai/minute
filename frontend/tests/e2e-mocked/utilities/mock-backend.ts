import type { Page } from '@playwright/test'
import type {
  JobStatus,
  MinuteListItem,
  MinuteVersionResponse,
  RecordingCreateResponse,
  SingleRecording,
  TemplateMetadata,
  TemplateResponse,
  TranscriptionCreateResponse,
  TranscriptionGetResponse,
} from '@/lib/client/types.gen'

import {
  json,
  routeMinuteVersions,
} from '@/tests/e2e-mocked/utilities/minute-versions-route'
import { meeting1 } from '../mocked-responses/mock-meeting-1'
import { meeting1Minutes } from '../mocked-responses/mock-meeting-1.minutes'
import { meeting1Recordings } from '../mocked-responses/mock-meeting-1.recordings'
import { meeting1Versions } from '../mocked-responses/mock-meeting-1.versions'
import { meeting2 } from '../mocked-responses/mock-meeting-2'
import { meeting2Minutes } from '../mocked-responses/mock-meeting-2.minutes'
import { meeting2Recordings } from '../mocked-responses/mock-meeting-2.recordings'
import { meeting2Versions } from '../mocked-responses/mock-meeting-2.versions'
import { templates } from '../mocked-responses/templates'
import { transcriptions } from '../mocked-responses/transcriptions'
import { usersMe } from '../mocked-responses/users.me'
import { userTemplates } from '../mocked-responses/user-templates'

type Scenario = {
  transcription: TranscriptionGetResponse
  minutes: Array<MinuteListItem>
  versions: Array<MinuteVersionResponse>
  recordings: Array<SingleRecording>
}

const SCENARIOS = {
  'meeting-1': {
    transcription: meeting1,
    minutes: meeting1Minutes,
    versions: meeting1Versions,
    recordings: meeting1Recordings,
  },
  'meeting-2': {
    transcription: meeting2,
    minutes: meeting2Minutes,
    versions: meeting2Versions,
    recordings: meeting2Recordings,
  },
} satisfies Record<string, Scenario>

type ScenarioName = keyof typeof SCENARIOS

type Mock = {
  method: string
  path: string
  status: number
  response: unknown
}

const UPLOAD_URL = 'https://blob.test.local/upload'

export async function mockBackend(
  page: Page,
  scenario: ScenarioName = 'meeting-1',
  status?: JobStatus
): Promise<void> {
  const files = SCENARIOS[scenario]

  const transcription: TranscriptionGetResponse = { ...files.transcription }
  const minutes = files.minutes
  const transcriptionId = transcription.id
  const minuteId = minutes[0]?.id
  const versions: MinuteVersionResponse[] = [...files.versions]

  const systemTemplates: TemplateMetadata[] = structuredClone(templates)
  const userTemplatesState: TemplateResponse[] = structuredClone(userTemplates)

  if (status) {
    transcription.status = status
    if (status !== 'completed') transcription.dialogue_entries = null
    transcription.error = status === 'failed' ? 'Transcription failed' : null
  }

  const mocks: Mock[] = [
    {
      method: 'GET',
      path: '/templates',
      status: 200,
      response: systemTemplates,
    },
    {
      method: 'GET',
      path: '/user-templates',
      status: 200,
      response: userTemplatesState,
    },
    {
      method: 'GET',
      path: '/users/me',
      status: 200,
      response: usersMe,
    },
    {
      method: 'POST',
      path: '/recordings',
      status: 200,
      response: {
        id: `${scenario}-recording`,
        upload_url: UPLOAD_URL,
      } satisfies RecordingCreateResponse,
    },
    {
      method: 'POST',
      path: '/transcriptions',
      status: 201,
      response: { id: transcriptionId } satisfies TranscriptionCreateResponse,
    },
    {
      method: 'GET',
      path: `/transcriptions/${transcriptionId}`,
      status: 200,
      response: transcription,
    },
    {
      method: 'GET',
      path: `/transcription/${transcriptionId}/minutes`,
      status: 200,
      response: minutes,
    },
    {
      method: 'GET',
      path: `/transcriptions/${transcriptionId}/recordings`,
      status: 200,
      response: files.recordings,
    },
    {
      method: 'GET',
      path: '/transcriptions',
      status: 200,
      response: transcriptions,
    },
  ]

  await page.route(`${UPLOAD_URL}**`, (route) =>
    route.fulfill({ status: 200, body: '' })
  )

  await page.route('**/api/proxy/mock_storage/**', (route) =>
    route.fulfill({ status: 200, contentType: 'audio/mpeg', body: '' })
  )

  await routeMinuteVersions(page, { minuteId, versions, scenario })

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

  await page.route('**/api/proxy/users/default-template', (route) => {
    if (route.request().method() !== 'PATCH') return route.fallback()
    const body = route.request().postDataJSON() as {
      template_id?: string | null
      template_name?: string | null
    }
    for (const t of userTemplatesState) t.is_default = t.id === body.template_id
    for (const t of systemTemplates)
      t.is_default = t.name === body.template_name
    return route.fulfill(json(200, usersMe))
  })

  await page.route('**/api/proxy/user-templates/*', (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    const { pathname } = new URL(route.request().url())
    const id = pathname.split('/').at(-1)
    const found = userTemplatesState.find((t) => t.id === id)
    if (!found) return route.fallback()
    return route.fulfill(json(200, found))
  })

  for (const mock of mocks) {
    await page.route(`**/api/proxy${mock.path}**`, (route) => {
      const { pathname } = new URL(route.request().url())
      if (pathname !== `/api/proxy${mock.path}`) return route.fallback()
      if (route.request().method() !== mock.method) return route.fallback()
      return route.fulfill(json(mock.status, mock.response))
    })
  }
}
