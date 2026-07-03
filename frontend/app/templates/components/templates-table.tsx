'use client'

import { DeleteTemplatesDialog } from '@/app/templates/components/delete-templates-dialog'
import {
  TemplateRowData,
  templateRowKey,
} from '@/app/templates/components/template-row'
import { TemplatesList } from '@/app/templates/components/templates-list'
import {
  getTemplatesTemplatesGetOptions,
  getUserTemplatesUserTemplatesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useEffect, useMemo, useRef, useState } from 'react'

const PAGE_SIZE = 10

function buildQueryString(page?: number): string {
  if (!page || page <= 1) return ''
  return `?page=${page}`
}

export const TemplatesTable = () => {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const router = useRouter()
  const currentPage = Number(searchParams.get('page')) || 1

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
        isDefault: false,
      })),
      ...defaultTemplates.map((t) => ({
        id: null,
        name: t.name,
        description: t.description,
        isDefault: true,
      })),
    ],
    [userTemplates, defaultTemplates]
  )

  const totalCount = rows.length
  const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1
  const pageRows = rows.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  )
  const pageKeys = pageRows.map(templateRowKey)
  const allOnPageSelected =
    pageKeys.length > 0 && pageKeys.every((key) => selectedIds.has(key))
  const someOnPageSelected = pageKeys.some((key) => selectedIds.has(key))

  const deletableIds = rows
    .filter((row) => !row.isDefault && selectedIds.has(templateRowKey(row)))
    .map((row) => row.id!)
  const deleteCount = deletableIds.length

  const isLoading = defaultsLoading || userLoading
  const isError = defaultsError || userError

  if (!isLoading && currentPage > totalPages) {
    router.replace(pathname + buildQueryString(totalPages))
  }

  useEffect(() => {
    setSelectedIds(new Set())
  }, [currentPage])

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

  return (
    <div>
      <div className="flex items-center justify-between">
        <div className="govuk-form-group govuk-!-width-one-half">
          <label className="govuk-label" htmlFor="search-templates">Search templates</label>
          <input
            id="search-templates"
            name="search-templates"
            type="text"
            className="govuk-input"
          />
        </div>
        <div className="govuk-form-group">
          <label className="govuk-label" htmlFor="filter">
            Filter by
          </label>
          <select className="govuk-select" id="filter" name="filter">
            <option value="">All</option>
          </select>
        </div>
      </div>
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
          {deleteCount > 0 && (
            <div className="govuk-button-group govuk-!-margin-bottom-0">
              <button
                type="button"
                className="govuk-link link--warning govuk-!-margin-0"
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
      ) : rows.length === 0 ? (
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
                    href={pathname + buildQueryString(currentPage - 1)}
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
                      href={pathname + buildQueryString(page)}
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
                    href={pathname + buildQueryString(currentPage + 1)}
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
  )
}
