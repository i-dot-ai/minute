'use client'

import { DeleteDialog } from '@/components/recent-meetings/delete-transcription-dialog'
import { RenameDialog } from '@/components/recent-meetings/rename-dialog'
import { TranscriptionCard } from '@/components/recent-meetings/transcription-card'
import { Button } from '@/components/ui/button'
import { TranscriptionMetadata } from '@/lib/client'
import { Edit2, Trash } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'

export const TranscriptionListItem = ({
  transcription,
}: {
  transcription: TranscriptionMetadata
}) => {
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [renameOpen, setRenameOpen] = useState(false)
  return (
    <>
      <Link
        href={`/transcriptions/${transcription.id}`}
        className="justify-between rounded-md border p-3 text-sm transition-colors hover:bg-slate-100 sm:flex"
      >
        <TranscriptionCard transcription={transcription} />
        <div className="mt-2 flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.preventDefault()
              setRenameOpen(true)
            }}
            className="text-xs hover:bg-slate-200"
          >
            <Edit2 /> Rename
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.preventDefault()
              setDeleteOpen(true)
            }}
            className="text-xs text-red-600 hover:bg-red-100"
          >
            <Trash color="red" /> Delete
          </Button>
        </div>
      </Link>
      <DeleteDialog
        open={deleteOpen}
        setOpen={setDeleteOpen}
        transcription={transcription}
      />
      <RenameDialog
        open={renameOpen}
        setOpen={setRenameOpen}
        transcription={transcription}
      />
    </>
  )
}
