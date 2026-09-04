'use client'

import { LoadingBar } from '@/components/ui/loading-bar'
import { RefreshCw } from 'lucide-react'
import { useEffect, useRef } from 'react'

export function RecordingFinishedState() {
  const headingRef = useRef<HTMLHeadingElement>(null)

  // The recording controls (including the focused stop button) unmount when this
  // renders, which would drop keyboard focus to <body>. The timeout lets the
  // stop dialog's own focus restoration run first so this focus call wins.
  useEffect(() => {
    const id = setTimeout(() => headingRef.current?.focus(), 0)
    return () => clearTimeout(id)
  }, [])

  return (
    <div className="govuk-!-margin-top-4" role="status">
      <div className="govuk-!-padding-5 govuk-!-padding-top-8 govuk-!-margin-top-5 bg-(--govuk-surface-background-colour)">
        <div className="inline-flex items-center gap-2">
          <RefreshCw className="size-4 animate-spin text-(--govuk-text-colour)" />
          <h2 className="govuk-heading-m govuk-!-margin-bottom-0">
            Uploading your recording...
          </h2>
        </div>
        <div className="govuk-!-margin-bottom-7 govuk-!-margin-top-6">
          <LoadingBar />
        </div>
      </div>
    </div>
  )
}
