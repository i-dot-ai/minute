'use client'

import { DeleteTemplatesDialog } from '@/app/templates/components/delete-templates-dialog'
import { templateRowKey } from '@/app/templates/components/template-row'
import { TemplatesList } from '@/app/templates/components/templates-list'
import { TemplateRowData } from '@/types/templates'
import {
  getTemplatesTemplatesGetOptions,
  getUserTemplatesUserTemplatesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import Fuse from 'fuse.js'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Search } from 'lucide-react'

const PAGE_SIZE = 20

type TypeFilter = 'all' | 'summary' | 'q-and-a' | 'system'

function parseTypeFilter(searchParams: URLSearchParams): TypeFilter {
  const filterBy = searchParams.get('filterBy')
  if (
    filterBy === 'summary' ||
    filterBy === 'q-and-a' ||
    filterBy === 'system'
  ) {
    return filterBy
  }
  return 'all'
}

function buildQueryString({
  page,
  typeFilter = 'all',
}: {
  page?: number
  typeFilter?: TypeFilter
}): string {
  const params = new URLSearchParams()
  if (page && page > 1) params.set('page', String(page))
  if (typeFilter !== 'all') params.set('filterBy', typeFilter)
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

function matchesFilters(row: TemplateRowData, typeFilter: TypeFilter): boolean {
  switch (typeFilter) {
    case 'summary':
      return row.format === 'document' && !row.isSystem
    case 'q-and-a':
      return row.format === 'form' && !row.isSystem
    case 'system':
      return row.isSystem
    default:
      return true
  }
}

export const TemplatesTable = () => {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const router = useRouter()
  const currentPage = Number(searchParams.get('page')) || 1
  const typeFilter = parseTypeFilter(searchParams)

  const {
    data: defaultTemplates = [],
    isLoading: defaultsLoading,
    isError: defaultsError,
  } = useQuery(getTemplatesTemplatesGetOptions())
  const {
    data: userTemplates = [],
    isLoading: userLoading,
    isError: userError,
  } = useQuery(getUserTemplatesUserTemplatesGetOptions())

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [search, setSearch] = useState('')
  const selectAllRef = useRef<HTMLInputElement>(null)

  const rows: TemplateRowData[] = useMemo(
    () => [
      ...userTemplates.map((t) => ({
        id: t.id,
        name: t.name,
        description: t.description,
        isSystem: false,
        format: t.type,
        is_default: t.is_default ?? false,
      })),
      ...defaultTemplates.map((t) => ({
        id: null,
        name: t.name,
        description: t.description,
        isSystem: true,
        format: 'document' as const,
        is_default: t.is_default ?? false,
      })),
    ],
    [userTemplates, defaultTemplates]
  )

  const fuse = useMemo(
    () =>
      new Fuse(rows, {
        keys: ['name', 'description'],
        threshold: 0.4,
        ignoreLocation: true,
      }),
    [rows]
  )

  const filteredRows = useMemo(() => {
    const query = search.trim()
    const searchedRows = query
      ? fuse.search(query).map((result) => result.item)
      : rows
    return searchedRows.filter((row) => matchesFilters(row, typeFilter))
  }, [rows, fuse, search, typeFilter])

  const totalCount = filteredRows.length
  const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1
  const pageRows = filteredRows.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  )
  const selectablePageKeys = pageRows
    .filter((row) => !row.isSystem)
    .map(templateRowKey)
  const allOnPageSelected =
    selectablePageKeys.length > 0 &&
    selectablePageKeys.every((key) => selectedIds.has(key))
  const someOnPageSelected = selectablePageKeys.some((key) =>
    selectedIds.has(key)
  )

  const deletableIds = filteredRows
    .filter((row) => !row.isSystem && selectedIds.has(templateRowKey(row)))
    .map((row) => row.id!)
  const deleteCount = deletableIds.length
  const hasSystemSelected = filteredRows.some(
    (row) => row.isSystem && selectedIds.has(templateRowKey(row))
  )

  const isLoading = defaultsLoading || userLoading
  const isError = defaultsError || userError

  if (!isLoading && currentPage > totalPages) {
    router.replace(
      pathname + buildQueryString({ page: totalPages, typeFilter })
    )
  }

  useEffect(() => {
    setSelectedIds(new Set())
  }, [currentPage, typeFilter, search])

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate =
        someOnPageSelected && !allOnPageSelected
    }
  }, [someOnPageSelected, allOnPageSelected])

  const toggleOne = (key: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (checked) {
        next.add(key)
      } else {
        next.delete(key)
      }
      return next
    })
  }

  const toggleAllOnPage = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (allOnPageSelected) {
        selectablePageKeys.forEach((key) => next.delete(key))
      } else {
        selectablePageKeys.forEach((key) => next.add(key))
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
    const value = e.target.value as TypeFilter
    router.replace(pathname + buildQueryString({ typeFilter: value }))
  }

  const startNumber = (currentPage - 1) * PAGE_SIZE + 1
  const endNumber = Math.min(currentPage * PAGE_SIZE, totalCount)

  return (
    <>
      <div className="govuk-grid-row flex items-end">
        <div className="govuk-grid-column-one-half">
          <form
            role="search"
            className="govuk-form-group relative"
            onSubmit={(e) => e.preventDefault()}
          >
            <Search
              className="pointer-events-none absolute top-1/2 left-3 size-5 -translate-y-1/2 text-(--govuk-text-colour)"
              aria-hidden="true"
            />
            <input
              id="search-templates"
              name="search-templates"
              type="search"
              className="govuk-input govuk-input--subtle govuk-!-padding-left-7"
              placeholder="Search templates"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </form>
        </div>
        <div className="govuk-grid-column-one-half">
          <div className="govuk-button-group">
            <Link
              className="govuk-button"
              role="button"
              href="/templates/create"
            >
              Create new template
            </Link>
          </div>
        </div>
      </div>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-full">
          <div className="govuk-!-margin-bottom-3 flex items-center justify-between">
            <div className="flex flex-1 items-center gap-2">
              {selectablePageKeys.length > 0 && (
                <div
                  className="govuk-checkboxes govuk-checkboxes--small govuk-checkboxes--subtle relative flex"
                  data-module="govuk-checkboxes"
                >
                  <input
                    ref={selectAllRef}
                    className="govuk-checkboxes__input"
                    id="select-all-templates"
                    name="select-all-templates"
                    type="checkbox"
                    checked={allOnPageSelected}
                    onChange={toggleAllOnPage}
                  />
                  <label
                    className="govuk-label govuk-checkboxes__label ml-3 whitespace-nowrap"
                    htmlFor="select-all-templates"
                  >
                    Select all
                  </label>
                </div>
              )}
              {deleteCount > 0 && (
                <div className="govuk-button-group govuk-!-margin-bottom-0">
                  <button
                    type="button"
                    className="govuk-link link--warning govuk-!-margin-0 govuk-!-margin-right-1"
                    onClick={() => setDeleteDialogOpen(true)}
                  >
                    Delete {deleteCount} selected
                  </button>
                </div>
              )}
            </div>
            <span className="govuk-visually-hidden" aria-live="polite">
              {deleteCount > 0 ? `${deleteCount} templates selected` : ''}
            </span>
            <p
              className="govuk-body govuk-!-margin-bottom-0 flex-1"
              role="status"
            >
              Showing {startNumber} to {endNumber} of {totalCount}
              {search.trim() && (
                <span className="govuk-visually-hidden">
                  {` results for “${search.trim()}”`}
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
                value={typeFilter}
                onChange={handleFilterChange}
              >
                <option value="all">All</option>
                <option value="summary">Summary</option>
                <option value="q-and-a">Q &amp; A</option>
                <option value="system">System</option>
              </select>
            </div>
          </div>
          {isLoading ? (
            <p className="govuk-body">Loading templates...</p>
          ) : isError ? (
            <p className="govuk-body">Error loading templates</p>
          ) : filteredRows.length === 0 ? (
            <p className="govuk-body" role="status">
              No templates found
            </p>
          ) : (
            <>
              <TemplatesList
                templates={pageRows}
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
                          buildQueryString({
                            page: currentPage - 1,
                            typeFilter,
                          })
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
                          href={
                            pathname + buildQueryString({ page, typeFilter })
                          }
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
                          buildQueryString({
                            page: currentPage + 1,
                            typeFilter,
                          })
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
          <DeleteTemplatesDialog
            open={deleteDialogOpen}
            setOpen={setDeleteDialogOpen}
            templateIds={deletableIds}
            onDeleted={() => setSelectedIds(new Set())}
          />
        </div>
      </div>
    </>
  )
}
