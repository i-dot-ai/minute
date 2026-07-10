import posthog from 'posthog-js'
import { useState } from 'react'
import { Copy } from 'lucide-react'

interface CopyButtonProps {
  textToCopy: string
  posthogEvent: string
  disabled?: boolean
  label?: string
  posthogProperties?: Record<string, string | number>
  onCopied?: () => void
}

function CopyButton({
  textToCopy,
  posthogEvent,
  disabled,
  label = 'Copy',
  posthogProperties,
  onCopied,
}: CopyButtonProps) {
  const [isCopied, setIsCopied] = useState(false)

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
      ...posthogProperties,
    })
    onCopied?.()
    setIsCopied(true)
    setTimeout(() => {
      setIsCopied(false)
    }, 2000)
  }

  return (
    <>
      <button
        className="govuk-button flex items-center gap-2 govuk-button--secondary"
        onClick={handleCopy}
        disabled={disabled}
      >
        <Copy className="size-4" />
        {label}
      </button>
      {isCopied && <p className="govuk-tag govuk-tag--green">Copied</p>}
    </>
  )
}

export default CopyButton
