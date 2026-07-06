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
import { Eye, EyeOff } from 'lucide-react'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useEffect, useMemo, useRef, useState } from 'react'

const PAGE_SIZE = 10

type TypeFilter = 'all' | 'summary' | 'q-and-a'

function parseTypeFilter(searchParams: URLSearchParams): TypeFilter {
  const filterBy = searchParams.get('filterBy')
  if (filterBy === 'summary' || filterBy === 'q-and-a') {
    return filterBy
  }
  return 'all'
}

function parseHideSystem(searchParams: URLSearchParams): boolean {
  return searchParams.get('hideSystemTemplates') === 'true'
}

function buildQueryString({
  page,
  typeFilter = 'all',
  hideSystem = false,
}: {
  page?: number
  typeFilter?: TypeFilter
  hideSystem?: boolean
}): string {
  const params = new URLSearchParams()
  if (page && page > 1) params.set('page', String(page))
  if (typeFilter !== 'all') params.set('filterBy', typeFilter)
  if (hideSystem) params.set('hideSystemTemplates', 'true')
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

function matchesFilters(
  row: TemplateRowData,
  typeFilter: TypeFilter,
  hideSystem: boolean
): boolean {
  if (hideSystem && row.isSystem) {
    return false
  }
  switch (typeFilter) {
    case 'summary':
      return row.format === 'document'
    case 'q-and-a':
      return row.format === 'form'
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
  const hideSystem = parseHideSystem(searchParams)

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

  const filteredRows = useMemo(
    () => rows.filter((row) => matchesFilters(row, typeFilter, hideSystem)),
    [rows, typeFilter, hideSystem]
  )

  const totalCount = filteredRows.length
  const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1
  const pageRows = filteredRows.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  )
  const pageKeys = pageRows.map(templateRowKey)
  const allOnPageSelected =
    pageKeys.length > 0 && pageKeys.every((key) => selectedIds.has(key))
  const someOnPageSelected = pageKeys.some((key) => selectedIds.has(key))

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
      pathname + buildQueryString({ page: totalPages, typeFilter, hideSystem })
    )
  }

  useEffect(() => {
    setSelectedIds(new Set())
  }, [currentPage, typeFilter, hideSystem])

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
        pageKeys.forEach((key) => next.delete(key))
      } else {
        pageKeys.forEach((key) => next.add(key))
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
    router.replace(
      pathname + buildQueryString({ typeFilter: value, hideSystem })
    )
  }

  const toggleHideSystem = () => {
    router.replace(
      pathname + buildQueryString({ typeFilter, hideSystem: !hideSystem })
    )
  }

  return (
    <>
      <div className="govuk-grid-row flex items-end">
        <div className="govuk-grid-column-one-half">
          <div className="govuk-form-group">
            <label className="govuk-label" htmlFor="search-templates">
              Search templates
            </label>
            <input
              id="search-templates"
              name="search-templates"
              type="text"
              className="govuk-input"
            />
          </div>
        </div>
        <div className="govuk-grid-column-one-quarter">
          <div className="govuk-form-group">
            <label className="govuk-label" htmlFor="filter">
              Filter by
            </label>
            <select
              className="govuk-select govuk-!-width-full"
              id="filter"
              name="filter"
              value={typeFilter}
              onChange={handleFilterChange}
            >
              <option value="all">All</option>
              <option value="summary">Summary</option>
              <option value="q-and-a">Q &amp; A</option>
            </select>
          </div>
        </div>
        <div className="govuk-grid-column-one-quarter">
          <div className="govuk-form-group">
            <button
              type="button"
              className="govuk-button govuk-button--secondary govuk-!-margin-0"
              onClick={toggleHideSystem}
            >
              {hideSystem ? (
                <Eye className="size-4" />
              ) : (
                <EyeOff className="size-4" />
              )}
              {hideSystem ? 'Show system templates' : 'Hide system templates'}
            </button>
          </div>
        </div>
      </div>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-full">
          <div className="govuk-!-margin-bottom-3 govuk-!-padding-bottom-2 flex items-center justify-between border-b border-(--govuk-border-colour)">
            <div className="flex items-center gap-2">
              <div
                className="govuk-checkboxes govuk-checkboxes--small relative flex"
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
                  disabled={pageRows.length === 0}
                />
                <label
                  className="govuk-label govuk-checkboxes__label ml-3 whitespace-nowrap"
                  htmlFor="select-all-templates"
                >
                  Select all
                </label>
              </div>
              {hasSystemSelected && (
                <p className="govuk-body govuk-!-margin-0 text-red-600">
                  (Cannot delete system templates)
                </p>
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
            <p className="govuk-body govuk-!-margin-bottom-0">
              Total: {totalCount}
            </p>
          </div>
          {isLoading ? (
            <p className="govuk-body">Loading templates...</p>
          ) : isError ? (
            <p className="govuk-body">Error loading templates</p>
          ) : filteredRows.length === 0 ? (
            <p className="govuk-body">No templates found</p>
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
                            hideSystem,
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
                            pathname +
                            buildQueryString({ page, typeFilter, hideSystem })
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
                            hideSystem,
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
