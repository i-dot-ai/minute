import type { SingleRecording } from '@/lib/client/types.gen'
import { STORAGE_HOST } from '@/tests/e2e-mocked/utilities/routes/general'

export const meeting2Recordings = [
  {
    id: 'bf6a1d78-5dba-4d81-9829-03db0607f5fe',
    url: `${STORAGE_HOST}/static/restricted/user-uploads/test@test.co.uk/bf6a1d78-5dba-4d81-9829-03db0607f5fe.mp3`,
    extension: '.mp3',
  },
  {
    id: 'cb517e37-33dd-416b-9e4f-267e88a8bc4c',
    url: `${STORAGE_HOST}/static/restricted/user-uploads/test@test.co.uk/9d06a97f-a454-4666-b4a8-8117358130a7.webm`,
    extension: '.webm',
  },
] satisfies Array<SingleRecording>
