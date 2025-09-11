export function linkCitations(content: string): string {
  const parts: string[] = []
  const regex = /\[(\d+)\]/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(content)) !== null) {
    const idx = match.index
    if (idx > lastIndex) {
      parts.push(content.slice(lastIndex, idx))
    }
    const citationNumber = parseInt(match[1], 10)
    const text = match[0]
    parts.push(`[[${citationNumber}]](${citationNumber})`)
    lastIndex = idx + text.length
  }
  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex))
  }
  return parts.join('')
}

export function CitationContent({
  linkChildren,
  href,
  onCitationClick,
}: {
  linkChildren: React.ReactNode
  href: string | undefined
  onCitationClick: (index: number, rect: DOMRect) => void
}) {
  const regex = /^\d+$/
  let match: RegExpExecArray | null
  match = regex.exec(href || '')

  if (match !== null) {
    const idx = match.index
    const text = match[0]
    const citationNumber = parseInt(match[0], 10)
    return (
      <span
        key={`${idx}-${citationNumber}`}
        className="citation-link cursor-pointer text-blue-600 underline"
        onClick={(e) => {
          const rect = (e.target as HTMLElement).getBoundingClientRect()
          onCitationClick(citationNumber, rect)
        }}
      >
        [{text}]
      </span>
    )
  }
  return <a href={href}>{linkChildren}</a>
}
