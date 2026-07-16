'use client'

import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
import { TranscriptionSidePanel } from '@/app/transcriptions/[transcriptionId]/MinuteTab/components/TranscriptionSidePanel'
import { listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export default function SummaryIndexPage({
  params: { transcriptionId },
}: {
  params: { transcriptionId: string }
}) {
  const router = useRouter()

  const { data: minutes = [], isSuccess: minutesLoaded } = useQuery({
    ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions(
      {
        path: { transcription_id: transcriptionId },
      }
    ),
  })

  useEffect(() => {
    if (minutesLoaded && minutes.length > 0) {
      router.replace(
        `/transcriptions/${transcriptionId}/summary/${minutes[0].id}`
      )
    }
  }, [minutesLoaded, minutes, router, transcriptionId])

  if (!minutesLoaded || minutes.length > 0) {
    return (
      <div className="flex items-center gap-2">
        <Loader2 className="animate-spin" />
        <p className="govuk-body govuk-!-margin-bottom-0">Loading...</p>
      </div>
    )
  }

  return (
    <div className="govuk-grid-row">
      <div className="govuk-grid-column-one-quarter">
        <TranscriptionSidePanel
          transcriptionId={transcriptionId}
          minutes={minutes}
        />
      </div>
      <div className="govuk-grid-column-three-quarters">
        <div className="govuk-!-margin-bottom-6 govuk-!-padding-bottom-3 border-b border-(--govuk-border-colour)">
          <NewMinuteDialog
            transcriptionId={transcriptionId}
            onCreated={() =>
              router.push(`/transcriptions/${transcriptionId}/summary`)
            }
          />
        </div>
        <p className="govuk-body">No summaries generated yet.</p>
      </div>
    </div>
  )
}
