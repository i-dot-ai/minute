import posthog from 'posthog-js'
import { Copy } from 'lucide-react'
import { toast } from 'sonner'

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
    toast.success('Copied to clipboard')
  }

  return (
    <button
      className="govuk-button govuk-button--secondary flex items-center gap-2"
      onClick={handleCopy}
      disabled={disabled}
    >
      <Copy className="size-4" />
      {label}
    </button>
  )
}

export default CopyButton
