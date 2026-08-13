'use client'

import { listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { use, useEffect } from 'react'

export default function SummaryIndexPage({
  params,
}: {
  params: Promise<{ transcriptionId: string }>
}) {
  const { transcriptionId } = use(params)
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
      <div className="govuk-!-padding-top-4 govuk-width-container govuk-width-container--with-secondary-nav">
        <div className="flex items-center gap-2">
          <Loader2 className="animate-spin" />
          <p className="govuk-body govuk-!-margin-bottom-0">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="govuk-!-padding-top-4 govuk-width-container govuk-width-container--with-secondary-nav">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-full">
          <h1 className="govuk-heading-m">No summary generated</h1>
          <p className="govuk-body">
            Click <strong>New Summary</strong> on the left panel to get started.
          </p>
        </div>
      </div>
    </div>
  )
}
