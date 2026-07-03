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
import { useEffect, useMemo, useRef, useState } from 'react'

export const TemplatesTable = () => {
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

  const rowKeys = rows.map(templateRowKey)
  const allSelected =
    rowKeys.length > 0 && rowKeys.every((key) => selectedIds.has(key))
  const someSelected = rowKeys.some((key) => selectedIds.has(key))

  const deletableIds = rows
    .filter((row) => !row.isDefault && selectedIds.has(templateRowKey(row)))
    .map((row) => row.id!)
  const deleteCount = deletableIds.length
  const totalCount = rows.length

  const isLoading = defaultsLoading || userLoading
  const isError = defaultsError || userError

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = someSelected && !allSelected
    }
  }, [someSelected, allSelected])

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

  const toggleAll = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (allSelected) {
        rowKeys.forEach((key) => next.delete(key))
      } else {
        rowKeys.forEach((key) => next.add(key))
      }
      return next
    })
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <input
          type="text"
          className="govuk-input govuk-!-width-one-half"
          placeholder="Search templates"
        />
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
              checked={allSelected}
              onChange={toggleAll}
              disabled={rows.length === 0}
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
        <TemplatesList
          templates={rows}
          selectedIds={selectedIds}
          onToggle={toggleOne}
        />
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
