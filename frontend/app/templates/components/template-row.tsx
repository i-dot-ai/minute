'use client'

import {
  duplicateUserTemplateUserTemplatesTemplateIdDuplicatePostMutation,
  getUserTemplatesUserTemplatesGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { TemplateRowData } from '@/types/templates'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CopyPlus } from 'lucide-react'
import Link from 'next/link'
import posthog from 'posthog-js'

export const templateRowKey = (template: TemplateRowData) =>
  template.id ?? `default:${template.name}`

export function TemplateTableRow({
  template,
  selectedIds,
  onToggle,
}: {
  template: TemplateRowData
  selectedIds?: Set<string>
  onToggle?: (id: string, checked: boolean) => void
}) {
  const queryClient = useQueryClient()
  const name = template.name || 'Untitled template'
  const rowKey = templateRowKey(template)
  const inputId = `template-${rowKey}`.replace(/\s+/g, '-')

  const duplicateMutation = useMutation({
    ...duplicateUserTemplateUserTemplatesTemplateIdDuplicatePostMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: getUserTemplatesUserTemplatesGetQueryKey(),
      })
      posthog.capture('template_duplicated')
    },
  })

  const handleDuplicate = () => {
    // Default templates have no id yet; duplication will be wired to a backend
    // endpoint later.
    if (!template.id) return
    duplicateMutation.mutate({ path: { template_id: template.id } })
  }

  return (
    <tr className="govuk-table__row relative border-b border-(--govuk-border-colour) hover:bg-[#f4f8fb]">
      <td>
        {!template.isSystem && (
          <div className="govuk-!-margin-right-2 flex items-center">
            <div
              className="govuk-checkboxes govuk-checkboxes--small flex"
              data-module="govuk-checkboxes"
            >
              <input
                className="govuk-checkboxes__input"
                id={inputId}
                name="template"
                disabled={template.isSystem}
                type="checkbox"
                checked={selectedIds?.has(rowKey) ?? false}
                onChange={(e) => onToggle?.(rowKey, e.target.checked)}
              />
              <label
                className="govuk-label govuk-checkboxes__label"
                htmlFor={inputId}
              >
                <span className="govuk-visually-hidden">Select {name}</span>
              </label>
            </div>
            <div className="govuk-button-group govuk-!-margin-bottom-0 govuk-!-margin-right-1 flex items-center justify-end">
              <button
                type="button"
                className="govuk-link govuk-link--no-visited-state govuk-!-margin-0 flex items-center gap-2 hover:cursor-pointer"
                onClick={handleDuplicate}
              >
                <CopyPlus className="size-4" />
                <span className="govuk-visually-hidden">Duplicate {name}</span>
              </button>
            </div>
          </div>
        )}
      </td>
      <td className="md:flex-1">
        <Link
          href={
            template.isSystem
              ? `/templates/system/${encodeURIComponent(template.name)}`
              : `/templates/${template.id}`
          }
          className="govuk-link govuk-link--no-visited-state govuk-link--no-underline relative flex flex-1 flex-col items-start gap-1 py-1 !text-(--govuk-text-colour) lg:flex-row lg:gap-2"
        >
          <span className="font-bold lg:min-w-60">{name}</span>{' '}
          <span className="govuk-body-s govuk-!-margin-0">
            {template.description}
          </span>
        </Link>
      </td>
      <td>
        <div className="govuk-!-padding-top-2 govuk-!-padding-bottom-2 flex items-center justify-end">
          {template.is_default && (
            <strong className="govuk-tag govuk-tag--blue govuk-!-margin-left-2">
              Default
            </strong>
          )}
          {template.isSystem ? (
            <strong className="govuk-tag govuk-tag--grey govuk-!-margin-left-2">
              System
            </strong>
          ) : (
            <strong className="govuk-tag govuk-tag--green govuk-!-margin-left-2">
              {template.format === 'document' ? 'Summary' : 'Q & A'}
            </strong>
          )}
        </div>
      </td>
    </tr>
  )
}
