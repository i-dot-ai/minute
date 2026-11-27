'use client'

import { X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

const tagClass =
  'govuk-tag govuk-!-margin-0 govuk-!-font-size-16 govuk-!-font-weight-regular !max-w-full break-words'

export function TranscriptionKeywords({ keywords }: { keywords?: string[] }) {
  const [expanded, setExpanded] = useState(false)
  if (!keywords?.length) return null

  return (
    <section
      aria-label="Keywords"
      className="govuk-!-margin-bottom-4 govuk-!-padding-bottom-4 flex flex-wrap gap-2 border-b border-(--govuk-border-colour)"
    >
      {(expanded ? keywords : keywords.slice(0, 8)).map((keyword) => (
        <span className={tagClass} key={keyword}>
          {keyword}
        </span>
      ))}
      {keywords.length > 8 && (
        <button
          type="button"
          className="govuk-link govuk-!-font-size-16"
          aria-expanded={expanded}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? 'Less' : 'More'}
        </button>
      )}
    </section>
  )
}

export function TranscriptionKeywordField({
  keywords,
  onChange,
  isLoading,
  isError,
  refetch,
  isSaving,
  saveError,
}: {
  keywords?: string[]
  onChange: (keywords: string[]) => void
  isLoading: boolean
  isError: boolean
  refetch: () => void
  isSaving: boolean
  saveError: boolean
}) {
  const [input, setInput] = useState<string | null>(null)
  const addButton = useRef<HTMLButtonElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const adding = input !== null

  useEffect(() => {
    if (adding) inputRef.current?.focus()
  }, [adding])

  const addPhrase = () => {
    const phrase = input?.trim().replace(/\s+/g, ' ')
    if (
      keywords &&
      phrase &&
      !isSaving &&
      !keywords.some(
        (keyword) => keyword.toLowerCase() === phrase.toLowerCase()
      )
    ) {
      onChange([...keywords, phrase])
    }
    setInput(null)
  }

  if (!keywords) {
    if (isLoading) return <p className="govuk-hint">Loading keywords…</p>
    return isError ? (
      <p className="govuk-body-s">
        Could not load keywords.{' '}
        <button type="button" className="govuk-link" onClick={refetch}>
          Try again
        </button>
      </p>
    ) : null
  }

  return (
    <div className="govuk-form-group govuk-!-padding-bottom-4 border-b border-(--govuk-border-colour)">
      <h2 className="govuk-heading-m govuk-!-margin-bottom-3">Keywords</h2>
      <ul
        className="flex flex-wrap items-center gap-2"
        aria-label="Current keywords"
      >
        {keywords.map((keyword) => (
          <li
            className={`${tagClass} !inline-flex items-center gap-1`}
            key={keyword}
          >
            {keyword}
            <button
              type="button"
              className="govuk-link inline-flex shrink-0 p-1"
              aria-label={`Remove ${keyword}`}
              disabled={isSaving}
              onClick={() => {
                onChange(keywords.filter((item) => item !== keyword))
                addButton.current?.focus()
              }}
            >
              <X className="size-4" aria-hidden="true" />
            </button>
          </li>
        ))}
        <li
          className={`${tagClass} !inline-flex min-h-8 items-center !bg-white inset-ring inset-ring-(--govuk-border-colour)`}
        >
          {input !== null ? (
            <input
              ref={inputRef}
              aria-label="New keyword"
              className="w-36 max-w-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--govuk-focus-colour)"
              maxLength={100}
              disabled={isSaving}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onBlur={addPhrase}
              onKeyDown={(event) => {
                if (event.nativeEvent.isComposing) return
                if (event.key === 'Escape') {
                  event.preventDefault()
                  setInput(null)
                } else if (event.key === 'Enter') {
                  event.preventDefault()
                  addPhrase()
                } else {
                  return
                }
                requestAnimationFrame(() => addButton.current?.focus())
              }}
            />
          ) : (
            <button
              ref={addButton}
              type="button"
              className="govuk-link !text-inherit"
              disabled={isSaving}
              onClick={() => setInput('')}
            >
              Add keyword
            </button>
          )}
        </li>
      </ul>
      {saveError && (
        <p className="govuk-error-message govuk-!-margin-top-2" role="alert">
          Could not save keywords. Try again.
        </p>
      )}
    </div>
  )
}
