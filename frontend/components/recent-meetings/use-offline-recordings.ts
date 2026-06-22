'use client'

import {
  RecordingDbItem,
  useRecordingDb,
} from '@/providers/transcription-db-provider'
import { useQuery } from '@tanstack/react-query'

export function sortRecordingsNewestFirst(
  recordings: RecordingDbItem[]
): RecordingDbItem[] {
  return [...recordings].sort(
    (a, b) => b.updated_at.valueOf() - a.updated_at.valueOf()
  )
}

export function useOfflineRecordings() {
  const { listRecordings } = useRecordingDb()
  return useQuery({
    queryKey: ['list-db-recordings'],
    queryFn: listRecordings,
  })
}
