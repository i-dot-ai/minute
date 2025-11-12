'use client'

import { StatusBadge } from '@/components/status-icon'
import { TranscriptionMetadata } from '@/lib/client'
import { Clock } from 'lucide-react'

export const TranscriptionCard = ({
  transcription,
  className,
}: {
  transcription: TranscriptionMetadata
  className?: string
}) => {
  const date = new Date(transcription.created_datetime)
  return (
    <div className={className}>
      <div className="mb-1 line-clamp-1 items-center gap-2 font-semibold overflow-ellipsis">
        {transcription.title || 'No title'}
      </div>
      <div className="text-muted-foreground flex items-center gap-2 text-xs">
        <div className="line-clamp-1 flex items-center gap-1">
          <Clock className="size-3.5" />
          <span className="line-clamp-1">
            {date.toDateString()} at {date.toLocaleTimeString()}
          </span>
        </div>
        <StatusBadge status={transcription.status} className="text-inherit" />
      </div>
    </div>
  )
}
