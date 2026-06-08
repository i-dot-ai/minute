'use client'

import { OfflineRecordings } from '@/components/recent-meetings/offline-recordings'
import { TranscriptionListItem } from '@/components/recent-meetings/transcription-list-item'
import { Button } from '@/components/ui/button'
import {
  getUserUsersMeGetOptions,
  listTranscriptionsTranscriptionsGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Info } from 'lucide-react'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'

export const PaginatedTranscriptions = () => {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const router = useRouter()
  const currentPage = Number(searchParams.get('page')) || 1
  const pageSize = 10
  const {
    data: paginatedResponse,
    isLoading,
    error,
  } = useQuery({
    ...listTranscriptionsTranscriptionsGetOptions({
      query: { page: currentPage, page_size: pageSize },
    }),
    refetchInterval: (query) =>
      !!query.state.data &&
        query.state.data.items?.some((t) =>
          ['awaiting_start', 'in_progress'].includes(t.status)
        )
        ? 5000
        : false,
    placeholderData: keepPreviousData,
  })

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

  return (
    <div>
      <OfflineRecordings />
      <div>
        <div >
          <h2 className="govuk-heading-m">Recent meetings:</h2>
          <p className="govuk-body">
            {totalCount} transcription{totalCount !== 1 ? 's' : ''}
          </p>
        </div>

        {user && user.data_retention_days && (
          <p className="govuk-body">
            <Info />
            Your data retention period is set to {user.data_retention_days}{' '}
            day
            {user.data_retention_days > 1 ? 's' : ''}. Change this in{' '}
            <Link
              href="/settings"
              className="govuk-link"
            >
              settings
            </Link>
            .
          </p>
        )}
      </div>
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <p className="govuk-body">Loading transcriptions...</p>
        </div>
      ) : error ? (
        <div className="flex items-center justify-center py-8">
          <p className="govuk-body">Error loading transcriptions</p>
        </div>
      ) : transcriptions.length === 0 ? (
        <div className="flex items-center justify-center py-8">
          <p className="govuk-body">No transcriptions found</p>
        </div>
      ) : (
        <>
          <ul className="govuk-list govuk-list--bullet">
            {transcriptions.map((transcription) => (
              <TranscriptionListItem
                transcription={transcription}
                key={transcription.id}
              />
            ))}
          </ul>
          {totalPages > 1 && (
            <div className="flex items-center justify-center space-x-2">
              {currentPage > 1 && (
                <Button variant="outline" size="sm" asChild>
                  <Link
                    href={pathname + `?page=${currentPage - 1}`}
                    scroll={false}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </Link>
                </Button>
              )}
              {getPageNumbers().map((page) => (
                <Button
                  key={page}
                  variant={currentPage === page ? 'default' : 'outline'}
                  size="sm"
                  className="min-w-10"
                  asChild
                >
                  <Link href={pathname + `?page=${page}`} scroll={false}>
                    {page}
                  </Link>
                </Button>
              ))}
              {currentPage < totalPages && (
                <Button variant="outline" size="sm" asChild>
                  <Link
                    href={pathname + `?page=${currentPage + 1}`}
                    scroll={false}
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                </Button>
              )}
            </div>
          )}
          <div className="mt-4 text-center text-sm text-gray-500">
            Page {currentPage} of {totalPages}
          </div>
        </>
      )}
    </div>
  )
}
