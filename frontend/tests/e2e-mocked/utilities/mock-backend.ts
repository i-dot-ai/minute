import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type { Page } from '@playwright/test'
import type {
  JobStatus,
  MinuteListItem,
  TranscriptionGetResponse,
} from '@/lib/client/types.gen'


type Mock = {
  method: string
  path: string
  status: number
  response: unknown
}

type Scenario = {
  transcription: string
  minutes: string
  versions: string
  recordings: string
}

type ScenarioName = keyof typeof SCENARIOS

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const RESPONSES_DIR = path.resolve(__dirname, '../mocked-responses')

const UPLOAD_URL = 'https://blob.test.local/upload'

const SCENARIOS: Record<string, Scenario> = {
  'meeting-1': {
    transcription: 'mock-meeting-1.json',
    minutes: 'mock-meeting-1.minutes.json',
    versions: 'mock-meeting-1.versions.json',
    recordings: 'mock-meeting-1.recordings.json',
  },
  'meeting-2': {
    transcription: 'mock-meeting-2.json',
    minutes: 'mock-meeting-2.minutes.json',
    versions: 'mock-meeting-2.versions.json',
    recordings: 'mock-meeting-2.recordings.json',
  },
}

function fixture<T = unknown>(file: string): T {
  return JSON.parse(readFileSync(path.join(RESPONSES_DIR, file), 'utf-8')) as T
}

export async function mockBackend(
  page: Page,
  scenario:  ScenarioName = 'meeting-1',
  status?: JobStatus
): Promise<void> {
  const files = SCENARIOS[scenario]

  const transcription = fixture<TranscriptionGetResponse>(files.transcription)
  const minutes = fixture<MinuteListItem[]>(files.minutes)
  const transcriptionId = transcription.id
  const minuteId = minutes[0]?.id

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
      response: fixture('templates.json'),
    },
    {
      method: 'GET',
      path: '/user-templates',
      status: 200,
      response: fixture('user-templates.json'),
    },
    {
      method: 'GET',
      path: '/users/me',
      status: 200,
      response: fixture('users.me.json'),
    },
    {
      method: 'POST',
      path: '/recordings',
      status: 200,
      response: { id: `${scenario}-recording`, upload_url: UPLOAD_URL },
    },
    {
      method: 'POST',
      path: '/transcriptions',
      status: 201,
      response: { id: transcriptionId },
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
      path: `/minutes/${minuteId}/versions`,
      status: 200,
      response: fixture(files.versions),
    },
    {
      method: 'GET',
      path: `/transcriptions/${transcriptionId}/recordings`,
      status: 200,
      response: fixture(files.recordings),
    },
    {
      method: 'GET',
      path: '/transcriptions',
      status: 200,
      response: fixture('transcriptions.json'),
    },
  ]

  await page.route(`${UPLOAD_URL}**`, (route) =>
    route.fulfill({ status: 200, body: '' })
  )

  for (const mock of mocks) {
    await page.route(`**/api/proxy${mock.path}`, (route) => {
      if (route.request().method() !== mock.method) return route.fallback()
      return route.fulfill({
        status: mock.status,
        contentType: 'application/json',
        body: JSON.stringify(mock.response),
      })
    })
  }
}
