'use client'

import { DeleteConfirmDialog } from '@/app/templates/components/delete-single-template-dialog'
import {
  deleteUserTemplateUserTemplatesTemplateIdDeleteMutation,
  duplicateUserTemplateUserTemplatesTemplateIdDuplicatePostMutation,
  getUserTemplatesUserTemplatesGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { TemplateRowData } from '@/types/templates'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import posthog from 'posthog-js'
import { toast } from 'sonner'

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

  const { mutate: deleteTemplate, isPending: isDeleting } = useMutation({
    ...deleteUserTemplateUserTemplatesTemplateIdDeleteMutation(),
    onSuccess: () => {
      toast.success('Template deleted')
      queryClient.invalidateQueries({
        queryKey: getUserTemplatesUserTemplatesGetQueryKey(),
      })
      posthog.capture('template_deleted')
    },
  })

  const handleDuplicate = () => {
    // Default templates have no id yet; duplication will be wired to a backend
    // endpoint later.
    if (!template.id) return
    duplicateMutation.mutate({ path: { template_id: template.id } })
  }

  return (
    <tr className="govuk-table__row group relative hover:bg-[#f4f8fb]">
      <td className="govuk-table__cell">
        {template.isSystem ? (
          <div className="govuk-!-margin-left-2">-</div>
        ) : (
          <div className="flex items-center gap-2">
            <div
              className="govuk-checkboxes govuk-checkboxes--small govuk-checkboxes--subtle"
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
                className="govuk-label govuk-checkboxes__label govuk-!-padding-0"
                htmlFor={inputId}
              >
                <span className="govuk-visually-hidden">Select {name}</span>
              </label>
            </div>
          </div>
        )}
      </td>
      <td className="govuk-table__cell w-full">
        <Link
          href={
            template.isSystem
              ? `/templates/system/${encodeURIComponent(template.name)}`
              : `/templates/${template.id}`
          }
          className="govuk-link govuk-link--no-visited-state govuk-link--no-underline govuk-!-margin-right-1 inline-block w-full group-has-[a:hover]:text-[var(--govuk-link-hover-colour,#0f385c)]! group-has-[a:hover]:underline! group-has-[a:hover]:decoration-[max(3px,.1875rem,.12em)]! group-has-[a:hover]:[text-decoration-skip-ink:none]!"
        >
          <span className="block">{name}</span>
          <span className="govuk-!-font-size-16 block !text-(--govuk-text-colour)">
            {template.description}
          </span>
          {/* </Link>
        </td>
      <td className="govuk-table__cell w-full">
        <Link
          tabIndex={-1}
          href={
            template.isSystem
              ? `/templates/system/${encodeURIComponent(template.name)}`
              : `/templates/${template.id}`
          }
          className="govuk-body-s govuk-!-margin-bottom-0 inline-block w-full"
        > */}
          {/* {template.description} */}
        </Link>
      </td>
      <td className="govuk-table__cell whitespace-nowrap">
        <div className="govuk-!-padding-top-2 govuk-!-padding-bottom-2 flex items-center justify-end">
          {template.is_default && (
            <strong className="govuk-tag govuk-tag--blue govuk-!-margin-right-2">
              Default
            </strong>
          )}
          {template.isSystem ? (
            <strong className="govuk-tag govuk-tag--grey govuk-!-margin-right-2">
              System
            </strong>
          ) : (
            <strong className="govuk-tag govuk-tag--green govuk-!-margin-right-2">
              {template.format === 'document' ? 'Summary' : 'Q & A'}
            </strong>
          )}
        </div>
      </td>
      <td className="govuk-table__cell whitespace-nowrap">
        {template.isSystem ? (
          <div className="text-center">-</div>
        ) : (
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="govuk-link govuk-link--no-underline govuk-link--no-visited-state govuk-!-margin-0 govuk-!-font-size-16 text-(--govuk-link-colour) hover:cursor-pointer"
              onClick={handleDuplicate}
              disabled={duplicateMutation.isPending || isDeleting}
            >
              Duplicate
              <span className="govuk-visually-hidden">{name}</span>
            </button>
            <DeleteConfirmDialog
              name={name}
              disabled={
                isDeleting || duplicateMutation.isPending || !template.id
              }
              onConfirm={() =>
                deleteTemplate({ path: { template_id: template.id! } })
              }
            />
          </div>
        )}
      </td>
    </tr>
  )
}
