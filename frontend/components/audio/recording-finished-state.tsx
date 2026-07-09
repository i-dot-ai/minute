'use client'

import { Loader2 } from 'lucide-react'
import { useEffect, useRef } from 'react'

export function RecordingFinishedState({
  isUploading,
}: {
  isUploading: boolean
}) {
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
      <div className="flex items-center gap-2">
        <Loader2
          className="size-5 animate-spin motion-reduce:animate-none"
          aria-hidden="true"
        />
        <h2
          ref={headingRef}
          tabIndex={-1}
          className="govuk-heading-m govuk-!-margin-bottom-0"
        >
          Recording finished
        </h2>
      </div>
      {isUploading && (
        <p className="govuk-hint govuk-!-margin-top-2 govuk-!-margin-bottom-0">
          Uploading your recording...
        </p>
      )}
    </div>
  )
}
