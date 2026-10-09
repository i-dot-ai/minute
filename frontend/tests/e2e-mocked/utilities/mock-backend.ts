import type { Page } from '@playwright/test'
import type {
  JobStatus,
  MinuteListItem,
  MinuteVersionResponse,
  RecordingCreateResponse,
  SingleRecording,
  TranscriptionCreateResponse,
  TranscriptionGetResponse,
} from '@/lib/client/types.gen'

import { meeting1 } from '../mocked-responses/mock-meeting-1'
import { meeting1Minutes } from '../mocked-responses/mock-meeting-1.minutes'
import { meeting1Recordings } from '../mocked-responses/mock-meeting-1.recordings'
import { meeting1Versions } from '../mocked-responses/mock-meeting-1.versions'
import { meeting2 } from '../mocked-responses/mock-meeting-2'
import { meeting2Minutes } from '../mocked-responses/mock-meeting-2.minutes'
import { meeting2Recordings } from '../mocked-responses/mock-meeting-2.recordings'
import { meeting2Versions } from '../mocked-responses/mock-meeting-2.versions'
import { transcriptions } from '../mocked-responses/transcriptions'
import { usersMe } from '../mocked-responses/users.me'

import { routeMinuteVersions } from './routes/versions'
import {
  routeStatic,
  type StaticMock,
  routeStorage,
  UPLOAD_URL,
} from './routes/general'
import { routeTemplates } from './routes/templates'
import { routeTranscription } from './routes/transcription'
import { routeUser } from './routes/user'

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

export async function mockBackend(
  page: Page,
  scenario: ScenarioName = 'meeting-1',
  status?: JobStatus
): Promise<void> {
  const scenarioData = SCENARIOS[scenario]

  const transcription: TranscriptionGetResponse = {
    ...scenarioData.transcription,
  }
  const minutes = scenarioData.minutes
  const transcriptionId = transcription.id
  const minuteId = minutes[0]?.id
  const versions: MinuteVersionResponse[] = [...scenarioData.versions]

  if (status) {
    transcription.status = status
    if (status !== 'completed') transcription.dialogue_entries = null
    transcription.error = status === 'failed' ? 'Transcription failed' : null
  }

  const staticMocks: StaticMock[] = [
    { method: 'GET', path: '/users/me', status: 200, response: usersMe },
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
      response: scenarioData.recordings,
    },
    {
      method: 'GET',
      path: '/transcriptions',
      status: 200,
      response: transcriptions,
    },
  ]

  await routeStorage(page)
  await routeTemplates(page)
  await routeMinuteVersions(page, { minuteId, versions, scenario })
  await routeTranscription(page, { transcription, minutes })
  await routeStatic(page, staticMocks)
  await routeUser(page)
}
