import { meeting1 } from '../mocked-responses/mock-meeting-1'
import { meeting1Minutes } from '../mocked-responses/mock-meeting-1.minutes'
import { meeting1Versions } from '../mocked-responses/mock-meeting-1.versions'
import { userTemplates } from '../mocked-responses/user-templates'
import { templates } from '../mocked-responses/templates'

export const PAGES_TO_TEST = [
  '/',
  `/new/status/${meeting1.id}`,
  `/transcriptions/${meeting1.id}/summary/${meeting1Minutes[0].id}?version=${meeting1Versions[0].id}`,
  `/transcriptions/${meeting1.id}/transcript`,
  '/templates',
  '/templates/create',
  '/templates/create?example=my-general',
  `/templates/system/${templates[0].name}`,
  `/templates/${userTemplates[0].id}`,
  '/support',
  '/privacy',
  '/unauthorised',
]
