'use client'

import { DeleteTranscriptionsDialog } from '@/components/recent-meetings/delete-transcriptions-dialog'
import { TranscriptionsList } from '@/components/recent-meetings/transcriptions-list'
import {
  sortRecordingsNewestFirst,
  useOfflineRecordings,
} from '@/components/recent-meetings/use-offline-recordings'
import { useTranscriptions } from '@/components/recent-meetings/use-transcriptions'
import { TranscriptionListFilter } from '@/lib/client'
import { useRecordingDb } from '@/providers/transcription-db-provider'
import { useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import { Search, FileText } from 'lucide-react'

const PAGE_SIZE = 20

type TranscriptionFilter = 'all' | 'incomplete' | TranscriptionListFilter

function parseFilterBy(searchParams: URLSearchParams): TranscriptionFilter {
  const filterBy = searchParams.get('filterBy')
  if (
    filterBy === 'expiring-soon' ||
    filterBy === 'failed' ||
    filterBy === 'incomplete'
  )
    return filterBy
  if (searchParams.get('expiring') === 'true') return 'expiring-soon'
  return 'all'
}

function buildQueryString(
  page?: number,
  filterBy: TranscriptionFilter = 'all',
  search = ''
): string {
  const params = new URLSearchParams()
  if (page && page > 1) params.set('page', String(page))
  if (filterBy !== 'all') params.set('filterBy', filterBy)
  if (search) params.set('q', search)
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export const PaginatedTranscriptions = () => {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const router = useRouter()
  const currentPage = Number(searchParams.get('page')) || 1
  const filterBy = parseFilterBy(searchParams)
  const search = searchParams.get('q') ?? ''
  const [searchInput, setSearchInput] = useState(search)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const selectAllRef = useRef<HTMLInputElement>(null)

  const {
    data: paginatedResponse,
    isLoading,
    error,
  } = useTranscriptions({
    page: currentPage,
    pageSize: PAGE_SIZE,
    filterBy:
      filterBy === 'all' || filterBy === 'incomplete' ? undefined : filterBy,
    search: search || undefined,
  })
  const { data: dbRecordings = [] } = useOfflineRecordings()
  const offlineRecordings = sortRecordingsNewestFirst(dbRecordings)
  const { removeRecording } = useRecordingDb()
  const queryClient = useQueryClient()
  const offlineIdSet = new Set(offlineRecordings.map((r) => r.recording_id))
  const selectedOfflineIds = [...selectedIds].filter((id) =>
    offlineIdSet.has(id)
  )
  const selectedTranscriptionIds = [...selectedIds].filter(
    (id) => !offlineIdSet.has(id)
  )

  if (paginatedResponse && paginatedResponse.total_pages < currentPage) {
    router.replace(
      pathname +
        buildQueryString(paginatedResponse.total_pages, filterBy, search)
    )
  }
  const transcriptions =
    filterBy === 'incomplete' ? [] : paginatedResponse?.items || []
  const visibleOfflineRecordings =
    !search &&
    (filterBy === 'incomplete' || (filterBy === 'all' && currentPage === 1))
      ? offlineRecordings
      : []
  const totalPages = paginatedResponse?.total_pages || 1
  const totalCount = paginatedResponse?.total_count || 0
  const offlineCount =
    !search && filterBy === 'all' ? offlineRecordings.length : 0
  const combinedTotalCount = totalCount + offlineCount
  const resultsStarting =
    (currentPage - 1) * PAGE_SIZE + 1 + (currentPage > 1 ? offlineCount : 0)
  const resultsEnding =
    Math.min(currentPage * PAGE_SIZE, totalCount) + offlineCount
  const pageIds = [
    ...visibleOfflineRecordings.map((r) => r.recording_id),
    ...transcriptions.map((t) => t.id),
  ]
  const allOnPageSelected =
    pageIds.length > 0 && pageIds.every((id) => selectedIds.has(id))
  const someOnPageSelected = pageIds.some((id) => selectedIds.has(id))

  useEffect(() => {
    setSelectedIds(new Set())
  }, [currentPage, filterBy, search])

  useEffect(() => {
    if (searchInput.trim() === search) return
    const timer = setTimeout(() => {
      router.replace(
        pathname + buildQueryString(undefined, filterBy, searchInput.trim())
      )
    }, 300)
    return () => clearTimeout(timer)
  }, [searchInput, search, filterBy, pathname, router])

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate =
        someOnPageSelected && !allOnPageSelected
    }
  }, [someOnPageSelected, allOnPageSelected])

  const toggleOne = (id: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (checked) {
        next.add(id)
      } else {
        next.delete(id)
      }
      return next
    })
  }

  const toggleAllOnPage = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (allOnPageSelected) {
        pageIds.forEach((id) => next.delete(id))
      } else {
        pageIds.forEach((id) => next.add(id))
      }
      return next
    })
  }

  const getPageNumbers = () => {
    const pages = []
    const maxPagesToShow = 5
    let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2))
    const endPage = Math.min(totalPages, startPage + maxPagesToShow - 1)

    if (endPage - startPage + 1 < maxPagesToShow) {
      startPage = Math.max(1, endPage - maxPagesToShow + 1)
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i)
    }
    return pages
  }

  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value as TranscriptionFilter
    router.replace(pathname + buildQueryString(undefined, value, search))
  }

  const handleSearchSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    router.replace(
      pathname + buildQueryString(undefined, filterBy, searchInput.trim())
    )
  }

  const selectedCount = selectedIds.size

  return (
    <div>
      <div className="flex items-center justify-between">
        <form
          role="search"
          className="govuk-form-group govuk-!-width-one-half relative"
          onSubmit={handleSearchSubmit}
        >
          <Search
            className="pointer-events-none absolute top-1/2 left-3 size-5 -translate-y-1/2 text-(--govuk-text-colour)"
            aria-hidden="true"
          />
          <input
            id="search-transcriptions"
            name="search-transcriptions"
            aria-label="Search transcriptions by title"
            type="search"
            className="govuk-input govuk-input--subtle !pl-10"
            placeholder="Search transcriptions by title"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </form>
      </div>
      {visibleOfflineRecordings.length > 0 && (
        <details className="govuk-details">
          <summary className="govuk-details__summary">
            <span className="govuk-details__summary-text">
              Why are some recordings marked &quot;Not uploaded&quot;?
            </span>
          </summary>
          <div className="govuk-details__text">
            <p className="govuk-body">
              These recordings are stored <strong> only in this browser</strong>{' '}
              — usually because the connection dropped before they finished
              uploading. They are not yet saved to your account and will be lost
              if this browser&apos;s data is cleared.
            </p>
            <p className="govuk-body">
              <strong>Upload</strong> saves a recording to your account and
              starts its transcription. <strong>Delete</strong> removes it
              permanently.
            </p>
            <p className="govuk-body">
              <strong>Uplaod failed</strong> means that retrying the upload
              failed again. Please{' '}
              <Link href="/support" className="govuk-link">
                contact support
              </Link>{' '}
              if the problem persists.
            </p>
          </div>
        </details>
      )}
      <div className="sm:hidden">
        <TranscriptionsFilter
          filterBy={filterBy}
          handleFilterChange={handleFilterChange}
        />
      </div>
      <div className="govuk-!-margin-bottom-1 flex items-center justify-between">
        <div className="flex flex-1 items-center gap-2">
          <div
            className="govuk-checkboxes govuk-checkboxes--small govuk-checkboxes--subtle relative flex"
            data-module="govuk-checkboxes"
          >
            <input
              ref={selectAllRef}
              className="govuk-checkboxes__input"
              id="select-all"
              name="select-all"
              type="checkbox"
              checked={allOnPageSelected}
              onChange={toggleAllOnPage}
              disabled={pageIds.length === 0}
            />
            <label
              className="govuk-label govuk-checkboxes__label ml-3 whitespace-nowrap"
              htmlFor="select-all"
            >
              Select all
            </label>
          </div>
          {selectedCount > 0 && (
            <div className="govuk-button-group govuk-!-margin-bottom-0">
              <button
                type="button"
                className="govuk-link link--warning govuk-!-margin-0"
                onClick={() => setDeleteDialogOpen(true)}
              >
                Delete {selectedCount} selected
              </button>
            </div>
          )}
        </div>
        <span className="govuk-visually-hidden" aria-live="polite">
          {selectedCount > 0 ? `${selectedCount} transcriptions selected` : ''}
        </span>
        <p
          className="govuk-body govuk-!-margin-bottom-0 hidden flex-1 md:block"
          role="status"
        >
          {filterBy === 'incomplete' ? (
            <>Showing {visibleOfflineRecordings.length} incomplete recordings</>
          ) : (
            <>
              {combinedTotalCount > 0 ? (
                <>
                  Showing {resultsStarting} to {resultsEnding} of{' '}
                  {combinedTotalCount}
                  {search && (
                    <span className="govuk-visually-hidden">
                      {` results for “${search}”`}
                    </span>
                  )}
                </>
              ) : (
                <>Showing 0 of 0 transcriptions</>
              )}
            </>
          )}
        </p>
        <div className="hidden sm:block">
          <TranscriptionsFilter
            filterBy={filterBy}
            handleFilterChange={handleFilterChange}
          />
        </div>
      </div>
      {isLoading ? (
        <p className="govuk-body" role="status">
          Loading transcriptions...
        </p>
      ) : error ? (
        <p className="govuk-body" role="status">
          Error loading transcriptions
        </p>
      ) : transcriptions.length === 0 &&
        visibleOfflineRecordings.length === 0 ? (
        <div className="govuk-!-margin-top-9 flex flex-col items-center justify-center gap-2">
          {search ? (
            <>
              <p className="govuk-body">
                No transcriptions found for <strong>{search}</strong>
              </p>
            </>
          ) : filterBy !== 'all' ? (
            <>
              <p className="govuk-body">No transcriptions match that filter</p>
              <p className="govuk-body">
                Change or clear the filter to see the full list
              </p>
              <Link
                href={pathname + buildQueryString(undefined, 'all', search)}
                className="govuk-button govuk-button--secondary"
              >
                Clear filter
              </Link>
            </>
          ) : (
            <>
              <FileText className="size-10 text-[#cecece]" />
              <p className="govuk-body govuk-!-margin-bottom-1">
                No transcriptions found
              </p>
              <Link href="/transcriptions" className="govuk-button">
                Start a new recording
              </Link>
            </>
          )}
        </div>
      ) : (
        <>
          <TranscriptionsList
            transcriptions={transcriptions}
            offlineRecordings={visibleOfflineRecordings}
            selectable
            selectedIds={selectedIds}
            onToggle={toggleOne}
          />
          {filterBy !== 'incomplete' && totalPages > 1 && (
            <nav
              className="govuk-pagination sm:flex sm:justify-center"
              aria-label="Pagination"
            >
              {currentPage > 1 && (
                <div className="govuk-pagination__prev">
                  <Link
                    className="govuk-link govuk-pagination__link"
                    href={
                      pathname +
                      buildQueryString(currentPage - 1, filterBy, search)
                    }
                    rel="prev"
                  >
                    <svg
                      className="govuk-pagination__icon govuk-pagination__icon--prev"
                      xmlns="http://www.w3.org/2000/svg"
                      height="13"
                      width="15"
                      aria-hidden="true"
                      focusable="false"
                      viewBox="0 0 15 13"
                    >
                      <path d="m6.5938-0.0078125-6.7266 6.7266 6.7441 6.4062 1.377-1.449-4.1856-3.9768h12.896v-2h-12.984l4.2931-4.293-1.414-1.414z"></path>
                    </svg>
                    <span className="govuk-pagination__link-title">
                      Previous
                      <span className="govuk-visually-hidden"> page</span>
                    </span>
                  </Link>
                </div>
              )}
              <ul className="govuk-pagination__list">
                {getPageNumbers().map((page) => (
                  <li
                    key={page}
                    className={`govuk-pagination__item ${page === currentPage ? 'govuk-pagination__item--current' : ''}`}
                  >
                    <Link
                      className="govuk-link govuk-pagination__link"
                      href={pathname + buildQueryString(page, filterBy, search)}
                      aria-label={`Page ${page}`}
                    >
                      {page}
                    </Link>
                  </li>
                ))}
              </ul>
              {currentPage < totalPages && (
                <div className="govuk-pagination__next">
                  <Link
                    className="govuk-link govuk-pagination__link"
                    href={
                      pathname +
                      buildQueryString(currentPage + 1, filterBy, search)
                    }
                    rel="next"
                  >
                    <span className="govuk-pagination__link-title">
                      Next
                      <span className="govuk-visually-hidden"> page</span>
                    </span>
                    <svg
                      className="govuk-pagination__icon govuk-pagination__icon--next"
                      xmlns="http://www.w3.org/2000/svg"
                      height="13"
                      width="15"
                      aria-hidden="true"
                      focusable="false"
                      viewBox="0 0 15 13"
                    >
                      <path d="m8.107-0.0078125-1.4136 1.414 4.2926 4.293h-12.986v2h12.896l-4.1855 3.9766 1.377 1.4492 6.7441-6.4062-6.7246-6.7266z"></path>
                    </svg>
                  </Link>
                </div>
              )}
            </nav>
          )}
        </>
      )}
      <DeleteTranscriptionsDialog
        open={deleteDialogOpen}
        setOpen={setDeleteDialogOpen}
        transcriptionIds={selectedTranscriptionIds}
        count={selectedCount}
        onDeleted={() => {
          selectedOfflineIds.forEach((id) => removeRecording(id))
          if (selectedOfflineIds.length > 0) {
            queryClient.invalidateQueries({
              queryKey: ['list-db-recordings'],
            })
          }
          setSelectedIds(new Set())
        }}
      />
    </div>
  )
}

const TranscriptionsFilter = ({
  filterBy,
  handleFilterChange,
}: {
  filterBy: TranscriptionFilter
  handleFilterChange: (e: React.ChangeEvent<HTMLSelectElement>) => void
}) => {
  return (
    <div className="govuk-form-group govuk-!-margin-bottom-0 flex flex-1 items-center gap-2 sm:justify-end">
      <label className="govuk-label" htmlFor="filter">
        Filter by
      </label>
      <select
        className="govuk-select govuk-select--subtle"
        id="filter"
        name="filter"
        value={filterBy}
        onChange={handleFilterChange}
      >
        <option value="all">All</option>
        <option value="expiring-soon">Expiring soon</option>
        <option value="failed">Failed</option>
        <option value="incomplete">Incomplete recordings</option>
      </select>
    </div>
  )
}
