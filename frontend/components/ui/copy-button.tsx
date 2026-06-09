import posthog from 'posthog-js'
import { useState } from 'react'

interface CopyButtonProps {
  textToCopy: string
  posthogEvent: string
}

function CopyButton({ textToCopy, posthogEvent }: CopyButtonProps) {

  const stripHtmlTags = (html: string) => {
    const tmp = document.createElement('DIV')
    tmp.innerHTML = html
    return tmp.textContent || tmp.innerText || ''
  }

  const handleCopy = async () => {
    try {
      // Try to copy as rich text first
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/html': new Blob([textToCopy], { type: 'text/html' }),
          'text/plain': new Blob([stripHtmlTags(textToCopy)], {
            type: 'text/plain',
          }),
        }),
      ])
    } catch {
      // Fallback for browsers that don't support clipboard.write
      await navigator.clipboard.writeText(stripHtmlTags(textToCopy))
    }

    posthog.capture(posthogEvent, {
      contentLength: textToCopy.length,
    })
  }

  return (
    <button
      className="govuk-button govuk-button--secondary"
      onClick={handleCopy}
    >
      Copy
    </button>
  )
}

export default CopyButton
