import { PaginatedTranscriptions } from '@/components/recent-meetings/paginated-transcriptions'
import { Loader2 } from 'lucide-react'
import { Suspense } from 'react'

export default function TranscriptionsPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <Suspense
        fallback={
          <div className="flex w-full items-center justify-center">
            <Loader2 className="animate-spin" />
          </div>
        }
      >
        <PaginatedTranscriptions />
      </Suspense>
    </div>
  )
}
