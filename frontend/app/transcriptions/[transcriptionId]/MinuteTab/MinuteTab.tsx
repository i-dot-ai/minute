'use client'

import { MinuteEditor } from '@/app/transcriptions/[transcriptionId]/MinuteTab/MinuteEditor'
import { NewMinuteDialog } from '@/app/transcriptions/[transcriptionId]/MinuteTab/NewMinuteDialog'
import { AudioWav } from '@/components/icons/AudioWav'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from '@/components/ui/select'
import { Transcription } from '@/lib/client'
import { listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import { AudioWaveform } from 'lucide-react'
import { useEffect, useState } from 'react'

export function MinuteTab({ transcription }: { transcription: Transcription }) {
  const { data: minutes = [], isLoading } = useQuery({
    ...listMinutesForTranscriptionTranscriptionTranscriptionIdMinutesGetOptions(
      {
        path: { transcription_id: transcription.id! },
      }
    ),
  })
  // Only see most recent minute of each template type
  const [selectedMinute, setSelectedMinute] = useState(0)
  useEffect(() => {
    setSelectedMinute(0)
  }, [minutes])

  if (isLoading) {
    return (
      <div className="flex w-full flex-col items-center justify-center">
        <AudioWav />
      </div>
    )
  }
  if (minutes.length == 0) {
    return (
      <div className="mt-4 flex flex-col items-center justify-center gap-2 text-slate-500">
        <AudioWaveform />
        <p>No minutes generated yet.</p>
        <div>
          <NewMinuteDialog transcriptionId={transcription.id!} />
        </div>
      </div>
    )
  }
  return (
    <>
      <div className="mb-4 flex flex-wrap gap-2">
        <Select
          value={`${selectedMinute}`}
          onValueChange={(v) => setSelectedMinute(Number(v))}
        >
          <SelectTrigger>{minutes[selectedMinute].template_name}</SelectTrigger>
          <SelectContent>
            {minutes.map((minute, index) => {
              const date = new Date(minute.updated_datetime)
              return (
                <SelectItem value={`${index}`} key={minute.id} className="">
                  <div>
                    <div>{minute.template_name}</div>
                    <div className="text-muted-foreground flex gap-1 text-xs">
                      {date.toDateString()} at {date.toLocaleTimeString()}
                    </div>
                  </div>
                </SelectItem>
              )
            })}
          </SelectContent>
        </Select>
        <NewMinuteDialog
          transcriptionId={transcription.id!}
          agenda={minutes[selectedMinute].agenda ?? undefined}
        />
      </div>
      <MinuteEditor
        transcription={transcription}
        minute={minutes[selectedMinute]}
      />
    </>
  )
}
