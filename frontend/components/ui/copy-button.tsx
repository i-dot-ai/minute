import { Button } from '@/components/ui/button'
import { Copy as CopyIcon } from 'lucide-react'
import posthog from 'posthog-js'
import { useState } from 'react'

interface CopyButtonProps {
  textToCopy: string
  posthogEvent: string
}

function CopyButton({ textToCopy, posthogEvent }: CopyButtonProps) {
  const [showCopied, setShowCopied] = useState(false)

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

    setShowCopied(true)
    setTimeout(() => setShowCopied(false), 2000)
  }

  return (
    <Button
      className="bg-emerald-500"
      onClick={handleCopy}
      title="Copy content"
      type="button"
    >
      <CopyIcon />
      {!showCopied && <span>Copy</span>}
      {showCopied && (
        <span className="animate-fade-in text-xs font-medium text-white">
          Copied!
        </span>
      )}
    </Button>
  )
}

export default CopyButton
