'use client'

import { MinuteExportState } from '@/app/transcriptions/[transcriptionId]/MinuteTab/minute-editor/minute-editor'
import CopyButton from '@/components/ui/copy-button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import { DialogueEntry } from '@/lib/client'
import convertAIMinutesToWordDoc from '@/lib/download-word-doc'
import { DownloadIcon } from 'lucide-react'
import posthog from 'posthog-js'
import { useCallback, useState } from 'react'

export const ExportSummaryDialog = ({
  exportState,
  title,
  dialogueEntries,
  disabled = false,
}: {
  exportState: MinuteExportState | null
  title?: string | null
  dialogueEntries?: DialogueEntry[] | null
  disabled?: boolean
}) => {
  const [open, setOpen] = useState(false)

  const handleWordDocDownload = useCallback(() => {
    if (!exportState) return
    posthog.capture('minutes_downloaded', {
      format: 'word',
      version_id: exportState.minuteVersionId,
    })

    convertAIMinutesToWordDoc(
      exportState.htmlContent,
      dialogueEntries || [],
      title || 'minutes.docx'
    )
    setOpen(false)
  }, [exportState, dialogueEntries, title])

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <button
        type="button"
        className="govuk-button govuk-button--secondary"
        disabled={disabled || !exportState}
        onClick={() => setOpen(true)}
        id="tour-export-summary"
      >
        <DownloadIcon className="size-4" />
        Export
      </button>
      <DialogContent>
        <DialogTitle className="govuk-heading-l">Export summary</DialogTitle>
        <DialogDescription className="govuk-body">
          Copy or download your summary.
        </DialogDescription>
        <div className="govuk-button-group govuk-!-margin-top-4">
          <button
            type="button"
            className="govuk-button govuk-button--secondary"
            onClick={handleWordDocDownload}
            disabled={!exportState}
          >
            <DownloadIcon className="size-4" />
            Download Word doc
          </button>
          <CopyButton
            textToCopy={exportState?.contentToCopy ?? ''}
            posthogEvent="minutes_content_copied"
            posthogProperties={{
              version_id: exportState?.minuteVersionId ?? '',
            }}
            disabled={!exportState}
            label="Copy summary"
            onCopied={() => setOpen(false)}
          />
        </div>
      </DialogContent>
    </Dialog>
  )
}
