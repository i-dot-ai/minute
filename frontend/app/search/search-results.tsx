'use client'

import { formatTime } from '@/components/audio/audio-player'
import { getTranscriptionDisplayTitle } from '@/components/recent-meetings/rename-transcription'
import type {
  TranscriptionSearchMatch,
  TranscriptionSearchSource,
} from '@/lib/client'
import { searchTranscriptionsTranscriptionsSearchGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { searchResultHref } from '@/lib/search-match'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, Search } from 'lucide-react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Fragment, useEffect, useState } from 'react'

const SOURCE_OPTIONS = [
  { value: 'title', label: 'Titles' },
  { value: 'transcript', label: 'Transcripts' },
  { value: 'summary', label: 'Summaries' },
  { value: 'speaker', label: 'Speakers' },
] satisfies { value: TranscriptionSearchSource; label: string }[]
const DEFAULT_SOURCES = SOURCE_OPTIONS.map(({ value }) => value)

function searchHref(
  keywords: string,
  sources: TranscriptionSearchSource[],
  page = 1
) {
  const params = new URLSearchParams()
  if (keywords) params.set('keywords', keywords)
  if (sources.join(',') !== DEFAULT_SOURCES.join(',')) {
    sources.forEach((source) => params.append('sources', source))
  }
  if (page > 1) params.set('page', String(page))
  return params.size ? `/search?${params}` : '/search'
}

function MatchSnippet({ match }: { match: TranscriptionSearchMatch }) {
  let offset = 0
  return (
    <>
      {match.snippet_start > 0 && '…'}
      {match.highlights.map(({ start, end }) => {
        const before = match.snippet.slice(offset, start)
        offset = end
        return (
          <Fragment key={start}>
            {before}
            <strong>{match.snippet.slice(start, end)}</strong>
          </Fragment>
        )
      })}
      {match.snippet.slice(offset)}
    </>
  )
}

export function SearchResults() {
  const router = useRouter()
  const params = useSearchParams()
  const keywords = (params.get('keywords') ?? '').trim()
  const sourceValues = params.getAll('sources')
  const sources: TranscriptionSearchSource[] = params.has('sources')
    ? SOURCE_OPTIONS.filter(({ value }) => sourceValues.includes(value)).map(
        ({ value }) => value
      )
    : DEFAULT_SOURCES
  const sourceKey = sources.join(',')
  const pageParam = Number(params.get('page'))
  const page = Number.isSafeInteger(pageParam) && pageParam > 0 ? pageParam : 1
  const [input, setInput] = useState(keywords)
  const [selectedSources, setSelectedSources] = useState(sources)
  const [sourceError, setSourceError] = useState(false)
  useEffect(() => setInput(keywords), [keywords])
  useEffect(() => {
    setSelectedSources(
      sourceKey ? (sourceKey.split(',') as TranscriptionSearchSource[]) : []
    )
    setSourceError(false)
  }, [sourceKey])
  const validQuery =
    keywords.length > 0 && keywords.length <= 100 && sources.length > 0
  const { data, isLoading, isError, refetch } = useQuery({
    ...searchTranscriptionsTranscriptionsSearchGetOptions({
      query: { search: keywords, sources, page, page_size: 20 },
    }),
    enabled: validQuery,
    retry: false,
  })
  const totalPages = data?.total_pages ?? 1
  const firstPage = Math.max(1, Math.min(page - 2, totalPages - 4))

  return (
    <>
      <form
        role="search"
        onSubmit={(event) => {
          event.preventDefault()
          if (!selectedSources.length) {
            setSourceError(true)
            return
          }
          setSourceError(false)
          router.push(searchHref(input.trim(), selectedSources))
        }}
      >
        <div className="govuk-form-group govuk-!-margin-bottom-2">
          <label className="govuk-visually-hidden" htmlFor="search-keywords">
            Search
          </label>
          <div className="govuk-hint" id="search-hint">
            Search titles, transcripts, all summary versions or speaker names.
          </div>
          <div className="flex">
            <input
              id="search-keywords"
              name="keywords"
              type="search"
              className="govuk-input min-w-0 flex-1"
              aria-describedby="search-hint"
              maxLength={100}
              value={input}
              onChange={(event) => setInput(event.target.value)}
            />
            <button
              className="govuk-button govuk-!-margin-bottom-0 !w-auto shrink-0"
              type="submit"
            >
              <Search className="size-5" aria-hidden="true" />
              <span className="govuk-visually-hidden">Search</span>
            </button>
          </div>
        </div>
        <div
          className={`govuk-form-group ${sourceError || !sources.length ? 'govuk-form-group--error' : ''}`}
        >
          <fieldset
            className="govuk-fieldset"
            aria-describedby={
              sourceError || !sources.length
                ? 'search-sources-error'
                : undefined
            }
          >
            <legend className="govuk-visually-hidden">Filter</legend>
            {(sourceError || !sources.length) && (
              <p
                id="search-sources-error"
                className="govuk-error-message"
                role="alert"
              >
                Select at least one search source.
              </p>
            )}
            <div className="flex items-start gap-x-3">
              <span
                className="govuk-body govuk-!-margin-bottom-0 govuk-!-margin-top-2"
                aria-hidden="true"
              >
                Filter:
              </span>
              <div className="govuk-checkboxes govuk-checkboxes--small flex min-w-0 flex-wrap gap-x-6">
                {SOURCE_OPTIONS.map(({ value, label }) => (
                  <div className="govuk-checkboxes__item" key={value}>
                    <input
                      className="govuk-checkboxes__input"
                      type="checkbox"
                      name="sources"
                      id={`search-source-${value}`}
                      value={value}
                      checked={selectedSources.includes(value)}
                      onChange={(event) => {
                        const selected = event.target.checked
                          ? [...selectedSources, value]
                          : selectedSources.filter((source) => source !== value)
                        setSelectedSources(
                          SOURCE_OPTIONS.filter((option) =>
                            selected.includes(option.value)
                          ).map((option) => option.value)
                        )
                        setSourceError(false)
                      }}
                    />
                    <label
                      className="govuk-label govuk-checkboxes__label"
                      htmlFor={`search-source-${value}`}
                    >
                      {label}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </fieldset>
        </div>
      </form>
      {!keywords && (
        <p className="govuk-body">
          Enter keywords to search your saved transcriptions and summaries.
        </p>
      )}
      {keywords.length > 100 && (
        <p className="govuk-error-message" role="alert">
          Enter 100 characters or fewer.
        </p>
      )}
      {validQuery && isLoading && (
        <p className="govuk-body" role="status">
          Searching…
        </p>
      )}
      {validQuery && isError && (
        <div role="alert">
          <p className="govuk-body">
            We could not load your search results. Please try again.
          </p>
          <button
            type="button"
            className="govuk-button govuk-button--secondary"
            onClick={() => refetch()}
          >
            Try again
          </button>
        </div>
      )}
      {validQuery && data && (
        <>
          <h2 className="govuk-heading-m" aria-live="polite">
            {data.total_count.toLocaleString('en-GB')}{' '}
            {data.total_count === 1 ? 'result' : 'results'}
          </h2>
          {data.items.length === 0 && (
            <p className="govuk-body">
              No results on this page. Try fewer keywords or a different search.
            </p>
          )}
          <ul className="govuk-list">
            {data.items.map((result) => {
              const bodyMatches = result.matches.filter(
                (match) => match.source !== 'title'
              )
              const matches = bodyMatches.length ? bodyMatches : result.matches
              const primary = matches[0]
              return (
                <li
                  key={result.id}
                  className="govuk-!-padding-bottom-5 govuk-!-margin-bottom-5 border-b border-(--govuk-border-colour)"
                >
                  <h3 className="govuk-heading-m govuk-!-margin-bottom-2">
                    <Link
                      className="govuk-link"
                      href={
                        primary
                          ? searchResultHref(result.id, primary)
                          : `/transcriptions/${result.id}`
                      }
                    >
                      {getTranscriptionDisplayTitle(
                        result.title,
                        result.status
                      )}
                    </Link>
                  </h3>
                  <p className="govuk-body-s govuk-!-margin-bottom-3 text-(--govuk-secondary-text-colour)">
                    Created:{' '}
                    {new Date(result.created_datetime).toLocaleDateString(
                      'en-GB',
                      { day: 'numeric', month: 'long', year: 'numeric' }
                    )}
                  </p>
                  {matches.map((match, index) => (
                    <div key={index} className="govuk-!-margin-bottom-3">
                      <Link
                        className="govuk-link govuk-link--no-underline block"
                        href={searchResultHref(result.id, match)}
                      >
                        <span className="govuk-body-s text-(--govuk-link-colour)">
                          {match.source === 'transcript'
                            ? `Transcript at ${formatTime(match.start_time ?? 0)}`
                            : match.source === 'speaker'
                              ? `Speaker at ${formatTime(match.start_time ?? 0)}`
                              : match.source === 'summary'
                                ? 'View matching summary version'
                                : 'Title'}
                        </span>
                        <p className="govuk-body govuk-!-margin-bottom-0 text-(--govuk-text-colour)">
                          <MatchSnippet match={match} />
                          {match.source === 'speaker' &&
                            match.speech_excerpt && (
                              <>: {match.speech_excerpt}</>
                            )}
                        </p>
                      </Link>
                    </div>
                  ))}
                  {result.matches_truncated && (
                    <p className="govuk-body-s govuk-!-margin-bottom-0">
                      More matches in this transcription or its summaries.
                    </p>
                  )}
                </li>
              )
            })}
          </ul>
          {totalPages > 1 && (
            <nav className="govuk-pagination" aria-label="Search results pages">
              {page > 1 && (
                <div className="govuk-pagination__prev">
                  <Link
                    className="govuk-link govuk-pagination__link"
                    rel="prev"
                    href={searchHref(keywords, sources, page - 1)}
                  >
                    <ArrowLeft
                      className="govuk-pagination__icon"
                      aria-hidden="true"
                    />
                    <span className="govuk-pagination__link-title">
                      Previous
                      <span className="govuk-visually-hidden"> page</span>
                    </span>
                  </Link>
                </div>
              )}
              <ul className="govuk-pagination__list">
                {Array.from(
                  { length: Math.min(5, totalPages) },
                  (_, index) => firstPage + index
                ).map((number) => (
                  <li
                    key={number}
                    className={`govuk-pagination__item ${number === page ? 'govuk-pagination__item--current' : ''}`}
                  >
                    <Link
                      className="govuk-link govuk-pagination__link"
                      href={searchHref(keywords, sources, number)}
                      aria-label={`Page ${number}`}
                      aria-current={number === page ? 'page' : undefined}
                    >
                      {number}
                    </Link>
                  </li>
                ))}
              </ul>
              {page < totalPages && (
                <div className="govuk-pagination__next">
                  <Link
                    className="govuk-link govuk-pagination__link"
                    rel="next"
                    href={searchHref(keywords, sources, page + 1)}
                  >
                    <span className="govuk-pagination__link-title">
                      Next<span className="govuk-visually-hidden"> page</span>
                    </span>
                    <ArrowRight
                      className="govuk-pagination__icon"
                      aria-hidden="true"
                    />
                  </Link>
                </div>
              )}
            </nav>
          )}
        </>
      )}
    </>
  )
}
