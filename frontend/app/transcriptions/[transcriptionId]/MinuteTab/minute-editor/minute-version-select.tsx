'use client'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from '@/components/ui/select'
import { ContentSource, MinuteVersionResponse } from '@/lib/client'
import { Edit, Wand2 } from 'lucide-react'
import { Dispatch, SetStateAction } from 'react'

const MapContentSource = ({ source }: { source: ContentSource }) => {
  if (source === 'ai_edit') {
    return (
      <div className="items-centre flex gap-1">
        <Wand2 />
        AI edited
      </div>
    )
  } else if (source === 'manual_edit') {
    return (
      <div className="items-centre flex gap-1">
        <Edit />
        Manually edited
      </div>
    )
  } else {
    return <div>First version generated</div>
  }
}

export const MinuteVersionSelect = ({
  minuteVersions,
  version,
  setVersion,
}: {
  minuteVersions: MinuteVersionResponse[]
  version: number
  setVersion: Dispatch<SetStateAction<number>>
}) => {
  return (
    <Select value={`${version}`} onValueChange={(v) => setVersion(Number(v))}>
      <SelectTrigger className="inline-flex">Edits</SelectTrigger>
      <SelectContent>
        {minuteVersions.map((v, index) => {
          const date = new Date(v.created_datetime!)
          return (
            <SelectItem key={v.id!} value={`${index}`}>
              <div className="flex w-full max-w-md flex-1 flex-col items-start">
                <div className="flex items-center gap-2">
                  <MapContentSource source={v.content_source} />
                  <div className="text-muted-foreground flex gap-1 text-xs">
                    {date.toLocaleDateString()}{' '}
                    {date.toLocaleTimeString(undefined, {
                      hour: 'numeric',
                      minute: 'numeric',
                    })}
                  </div>
                </div>
                {v.ai_edit_instructions && (
                  <div className="border-l-2 pl-2">
                    <q>{v.ai_edit_instructions}</q>
                  </div>
                )}
              </div>
            </SelectItem>
          )
        })}
      </SelectContent>
    </Select>
  )
}
