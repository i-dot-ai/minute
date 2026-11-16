import type { TranscriptionSearchMatch } from '@/lib/client'

export function searchResultHref(
  transcriptionId: string,
  match: TranscriptionSearchMatch
): string {
  const base = `/transcriptions/${transcriptionId}`
  if (match.source === 'title') return base
  const fragment = new URLSearchParams({
    text: match.snippet,
    offset: String(match.snippet_start),
    highlight: String(match.highlights[0]?.start ?? 0),
  })
  if (match.source === 'transcript' || match.source === 'speaker') {
    fragment.set('entry', String(match.entry_index))
    if (match.source === 'speaker') fragment.set('source', 'speaker')
    return `${base}/transcript#search-match?${fragment}`
  }
  return `${base}/summary/${match.minute_id}?version=${match.minute_version_id}#search-match?${fragment}`
}

export function readSearchMatch() {
  if (!window.location.hash.startsWith('#search-match?')) return null
  const params = new URLSearchParams(
    window.location.hash.slice('#search-match?'.length)
  )
  const text = params.get('text') ?? ''
  const offset = Number(params.get('offset'))
  const highlight = Number(params.get('highlight'))
  const entry = params.has('entry') ? Number(params.get('entry')) : null
  if (
    !text ||
    text.length > 1_000 ||
    !Number.isSafeInteger(offset) ||
    offset < 0 ||
    !Number.isSafeInteger(highlight) ||
    highlight < 0 ||
    highlight >= text.length ||
    (entry !== null && (!Number.isSafeInteger(entry) || entry < 0))
  )
    return null
  return {
    text,
    offset,
    highlight,
    entry,
    speaker: params.get('source') === 'speaker',
  }
}

const BLOCK_TAGS = new Set([
  'P',
  'BR',
  'DIV',
  'LI',
  'UL',
  'OL',
  'H1',
  'H2',
  'H3',
  'H4',
  'H5',
  'H6',
  'BLOCKQUOTE',
  'PRE',
  'HR',
  'TABLE',
  'TR',
  'TD',
  'TH',
  'SECTION',
])

export function findSearchPassage(
  text: string,
  match: NonNullable<ReturnType<typeof readSearchMatch>>
): number {
  let start = -1
  for (
    let index = text.indexOf(match.text);
    index !== -1;
    index = text.indexOf(match.text, index + 1)
  ) {
    if (
      start === -1 ||
      Math.abs(index - match.offset) < Math.abs(start - match.offset)
    )
      start = index
  }
  return start
}

// Match the backend's HTML text extraction, including words split by inline formatting.
export function scrollToSummaryMatch(
  root: HTMLElement,
  match: NonNullable<ReturnType<typeof readSearchMatch>>
): boolean {
  const chunks: { text: string; node: Text | null; start: number }[] = []
  let length = 0
  const append = (text: string, node: Text | null) => {
    chunks.push({ text, node, start: length })
    length += text.length
  }
  const visit = (node: Node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      append(node.textContent ?? '', node as Text)
    } else if (node instanceof HTMLElement) {
      if (['SCRIPT', 'STYLE', 'HEAD', 'TEMPLATE'].includes(node.tagName)) return
      const block = BLOCK_TAGS.has(node.tagName)
      if (block) append(' ', null)
      node.childNodes.forEach(visit)
      if (block) append(' ', null)
    }
  }
  visit(root)
  const raw = chunks.map((chunk) => chunk.text).join('')
  const text = raw.replace(/\s+/g, ' ').trim()
  const start = findSearchPassage(text, match)
  if (start === -1) return false
  const target = start + match.highlight
  let normalisedOffset = 0
  for (const word of raw.matchAll(/\S+/g)) {
    if (target < normalisedOffset + word[0].length) {
      const rawOffset = word.index + target - normalisedOffset
      const chunk = chunks.find(
        (part) =>
          part.node &&
          part.start <= rawOffset &&
          rawOffset < part.start + part.text.length
      )
      const element = chunk?.node?.parentElement?.closest<HTMLElement>(
        'p, li, h1, h2, h3, h4, h5, h6, pre'
      )
      if (!element) return false
      element.tabIndex = -1
      element.focus({ preventScroll: true })
      element.scrollIntoView({ block: 'center' })
      return true
    }
    normalisedOffset += word[0].length + 1
  }
  return false
}
