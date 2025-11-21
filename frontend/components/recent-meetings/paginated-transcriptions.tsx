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
import { usePathname, useSearchParams } from 'next/navigation'

export const PaginatedTranscriptions = () => {
  const { data: user } = useQuery({ ...getUserUsersMeGetOptions() })
  const searchParams = useSearchParams()
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

  const pathname = usePathname()

  return (
    <div>
      <OfflineRecordings />
      <div className="pb-2">
        <div className="flex items-center justify-between pb-2">
          <h1 className="text-2xl font-bold">Recent meetings:</h1>
          <div className="text-sm text-gray-600">
            {totalCount} transcription{totalCount !== 1 ? 's' : ''}
          </div>
        </div>
        {user && user.data_retention_days && (
          <div className="text-muted-foreground flex items-center gap-1 py-1 text-sm">
            <div className="mb-[2px]">
              <Info className="inline h-4 w-4" />
            </div>
            <div>
              Your data retention period is set to {user.data_retention_days}{' '}
              day
              {user.data_retention_days > 1 ? 's' : ''}. Change this in{' '}
              <Link
                href="/settings"
                className="inline text-sky-700 underline hover:decoration-2"
              >
                settings
              </Link>
              .
            </div>
          </div>
        )}
      </div>
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="text-gray-500">Loading transcriptions...</div>
        </div>
      ) : error ? (
        <div className="flex items-center justify-center py-8">
          <div className="text-red-500">Error loading transcriptions</div>
        </div>
      ) : transcriptions.length === 0 ? (
        <div className="flex items-center justify-center py-8">
          <div className="text-gray-500">No transcriptions found</div>
        </div>
      ) : (
        <>
          <ul className="mb-6 flex flex-col gap-2">
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
