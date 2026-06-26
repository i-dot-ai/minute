'use client'

import { RecentOfflineRecordingsSection } from '@/components/recent-meetings/recent-offline-recordings-section'
import { TranscriptionsList } from '@/components/recent-meetings/transcriptions-list'
import { useTranscriptions } from '@/components/recent-meetings/use-transcriptions'
import { getUserUsersMeGetOptions } from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { Suspense } from 'react'

const PAGE_SIZE = 10

export const PaginatedTranscriptions = () => {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const router = useRouter()
  const currentPage = Number(searchParams.get('page')) || 1
  const expiring = searchParams.get('expiring') === 'true'
  const {
    data: paginatedResponse,
    isLoading,
    error,
  } = useTranscriptions({ page: currentPage, pageSize: PAGE_SIZE, expiring })

  if (paginatedResponse && paginatedResponse.total_pages < currentPage) {
    router.replace(pathname + `?page=${paginatedResponse.total_pages}`)
  }
  const transcriptions = paginatedResponse?.items || []
  const totalPages = paginatedResponse?.total_pages || 1
  const totalCount = paginatedResponse?.total_count || 0

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
    const value = e.target.value
    if (value === 'all') {
      router.replace(pathname)
    } else {
      router.replace(pathname + `?expiring=true`)
    }
  }

  return (
    <div>
      {user && user.data_retention_days && (
        <p className="govuk-body">
          Your data retention period is set to {user.data_retention_days} day
          {user.data_retention_days > 1 ? 's' : ''}. Change this in{' '}
          <Link href="/settings" className="govuk-link">
            settings
          </Link>
          .
        </p>
      )}
      <Suspense fallback={null}>
        <RecentOfflineRecordingsSection />
      </Suspense>
      <div className="govuk-!-margin-bottom-6 flex items-end justify-between">
        <div className="govuk-form-group govuk-!-margin-bottom-0">
          <label className="govuk-label" htmlFor="filter">
            Filter by
          </label>
          <select
            className="govuk-select"
            id="filter"
            name="filter"
            onChange={handleFilterChange}
          >
            <option value="all" selected={!expiring}>
              All
            </option>
            <option value="expiring" selected={expiring}>
              Expiring soon
            </option>
          </select>
        </div>
        <p className="govuk-body govuk-!-margin-bottom-0">
          Total: {totalCount}
        </p>
      </div>
      {isLoading ? (
        <p className="govuk-body">Loading transcriptions...</p>
      ) : error ? (
        <p className="govuk-body">Error loading transcriptions</p>
      ) : transcriptions.length === 0 ? (
        <p className="govuk-body">No transcriptions found</p>
      ) : (
        <>
          <TranscriptionsList transcriptions={transcriptions} />
          {totalPages > 1 && (
            <nav
              className="govuk-pagination flex justify-center"
              aria-label="Pagination"
            >
              {currentPage > 1 && (
                <div className="govuk-pagination__prev">
                  <a
                    className="govuk-link govuk-pagination__link"
                    href={`${pathname}?page=${currentPage - 1}`}
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
                  </a>
                </div>
              )}
              <ul className="govuk-pagination__list">
                {getPageNumbers().map((page) => (
                  <li key={page} className="govuk-pagination__item">
                    <a
                      className="govuk-link govuk-pagination__link"
                      href={`${pathname}?page=${page}`}
                      aria-label={`Page ${page}`}
                    >
                      {page}
                    </a>
                  </li>
                ))}
              </ul>
              {currentPage < totalPages && (
                <div className="govuk-pagination__next">
                  <a
                    className="govuk-link govuk-pagination__link"
                    href={`${pathname}?page=${currentPage + 1}`}
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
                  </a>
                </div>
              )}
            </nav>
          )}
        </>
      )}
    </div>
  )
}
