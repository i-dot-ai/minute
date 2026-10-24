import type { SingleRecording } from '@/lib/client/types.gen'
import { STORAGE_HOST } from '@/tests/e2e-mocked/utilities/routes/general'

export const meeting1Recordings = [
  {
    id: '413b816a-e447-4b01-be3f-7209e5a5061d',
    url: `${STORAGE_HOST}/static/restricted/user-uploads/test@test.co.uk/d3fe432d-da5f-4b44-b9ed-c197e31db44f.mp3`,
    extension: '.mp3',
  },
] satisfies Array<SingleRecording>
