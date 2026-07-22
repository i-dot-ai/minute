'use client'

import { DeleteTranscriptionsDialog } from '@/components/recent-meetings/delete-transcriptions-dialog'
import { RecentOfflineRecordingsSection } from '@/components/recent-meetings/recent-offline-recordings-section'
import { TranscriptionsList } from '@/components/recent-meetings/transcriptions-list'
import { useTranscriptions } from '@/components/recent-meetings/use-transcriptions'
import { TranscriptionListFilter } from '@/lib/client'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useRef, useState } from 'react'
import { Search } from 'lucide-react'

const PAGE_SIZE = 20

type TranscriptionFilter = 'all' | TranscriptionListFilter

function parseFilterBy(searchParams: URLSearchParams): TranscriptionFilter {
  const filterBy = searchParams.get('filterBy')
  if (filterBy === 'expiring-soon' || filterBy === 'failed') return filterBy
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
    filterBy: filterBy === 'all' ? undefined : filterBy,
    search: search || undefined,
  })

  if (paginatedResponse && paginatedResponse.total_pages < currentPage) {
    router.replace(
      pathname +
        buildQueryString(paginatedResponse.total_pages, filterBy, search)
    )
  }
  const transcriptions = paginatedResponse?.items || []
  const totalPages = paginatedResponse?.total_pages || 1
  const totalCount = paginatedResponse?.total_count || 0
  const resultsStarting = (currentPage - 1) * PAGE_SIZE + 1
  const resultsEnding = Math.min(currentPage * PAGE_SIZE, totalCount)
  const pageIds = transcriptions.map((t) => t.id)
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
            className="govuk-input govuk-input--subtle govuk-!-padding-left-7"
            placeholder="Search transcriptions by title"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </form>
      </div>
      <Suspense fallback={null}>
        <RecentOfflineRecordingsSection />
      </Suspense>
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
              disabled={transcriptions.length === 0}
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
        <p className="govuk-body govuk-!-margin-bottom-0 flex-1" role="status">
          Showing {resultsStarting} to {resultsEnding} of {totalCount}
          {search && (
            <span className="govuk-visually-hidden">
              {` results for “${search}”`}
            </span>
          )}
        </p>

        <div className="govuk-form-group govuk-!-margin-bottom-0 flex flex-1 items-center justify-end gap-2">
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
          </select>
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
      ) : transcriptions.length === 0 ? (
        <p className="govuk-body" role="status">
          No transcriptions found
        </p>
      ) : (
        <>
          <TranscriptionsList
            transcriptions={transcriptions}
            selectable
            selectedIds={selectedIds}
            onToggle={toggleOne}
          />
          {totalPages > 1 && (
            <nav
              className="govuk-pagination flex justify-center"
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
                  <li key={page} className="govuk-pagination__item">
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
        transcriptionIds={[...selectedIds]}
        onDeleted={() => setSelectedIds(new Set())}
      />
    </div>
  )
}
