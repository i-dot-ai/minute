'use client'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  deleteUserTemplateUserTemplatesTemplateIdDeleteMutation,
  duplicateUserTemplateUserTemplatesTemplateIdDuplicatePostMutation,
  getUserTemplatesUserTemplatesGetQueryKey,
} from '@/lib/client/@tanstack/react-query.gen'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CopyPlus, TrashIcon } from 'lucide-react'
import Link from 'next/link'
import posthog from 'posthog-js'

export type TemplateRowData = {
  id: string | null
  name: string
  description: string
  isDefault: boolean
}

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

  const deleteMutation = useMutation({
    ...deleteUserTemplateUserTemplatesTemplateIdDeleteMutation(),
    onSuccess: () => {
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
    <tr className="govuk-table__row relative flex gap-4 items-center border-b border-(--govuk-border-colour) hover:bg-[#f4f8fb]">
      <td className="govuk-!-padding-0">
        <div
          className="govuk-checkboxes govuk-checkboxes--small flex"
          data-module="govuk-checkboxes"
        >
          <input
            className="govuk-checkboxes__input"
            id={inputId}
            name="template"
            type="checkbox"
            checked={selectedIds?.has(rowKey) ?? false}
            onChange={(e) => onToggle?.(rowKey, e.target.checked)}
          />
          <label className="govuk-label govuk-checkboxes__label" htmlFor={inputId}>
            <span className="govuk-visually-hidden">Select {name}</span>
          </label>
        </div>
      </td>
      <td className="govuk-!-padding-0 flex-1">
        <Link
          href={`/templates/${template.id}`}
          className="govuk-link govuk-link--no-visited-state govuk-link--no-underline relative flex flex-col lg:flex-row flex-1 items-baseline gap-1 lg:gap-2 !text-(--govuk-text-colour) py-1 lg:py-0"
        >
          <span className="font-bold lg:min-w-60">{name}</span>{' '}<span className="govuk-body-s govuk-!-margin-0">{template.description}</span>
        </Link>
      </td>
      <td className="govuk-!-padding-0">
        {template.isDefault ? (
          <strong className="govuk-tag govuk-!-margin-right-2">
            System
          </strong>
        ) : (
          <strong className="govuk-tag govuk-tag--green govuk-!-margin-right-2">
            Custom
          </strong>
        )}
      </td>
      <td className="govuk-!-padding-0">
        <div className="govuk-button-group govuk-!-margin-bottom-0 flex justify-end items-center">
          <button
            type="button"
            className="govuk-link govuk-link--no-visited-state flex items-center gap-2 hover:cursor-pointer"
            onClick={handleDuplicate}
          >
            <CopyPlus className="size-4" />
            <span className="govuk-visually-hidden">Duplicate {name}</span>
          </button>
          <DeleteConfirmDialog
            name={name}
            disabled={template.isDefault}
            onConfirm={() =>
              deleteMutation.mutate({ path: { template_id: template.id! } })
            }
          />
        </div>
      </td>
    </tr>
  )
}

const DeleteConfirmDialog = ({
  name,
  disabled,
  onConfirm,
}: {
  name: string
  disabled: boolean
  onConfirm: () => void
}) => (
  <AlertDialog>
    <AlertDialogTrigger asChild>
      <button className={`govuk-link link--warning flex items-center gap-2 hover:cursor-pointer ${disabled ? '!text-gray-500 opacity-50 !cursor-not-allowed' : ''}`} disabled={disabled}>
        <TrashIcon className="size-4" />
        <span className="govuk-visually-hidden">Delete {name}</span>
      </button>
    </AlertDialogTrigger>
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle className="govuk-heading-l">
          Delete template
        </AlertDialogTitle>
        <AlertDialogDescription className="govuk-body">
          Are you sure you want to delete <strong>{name}</strong>? This action
          cannot be undone.
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter className="govuk-button-group sm:justify-start">
        <AlertDialogAction asChild onClick={onConfirm}>
          <button type="button" className="govuk-button govuk-button--warning">
            Delete
          </button>
        </AlertDialogAction>
        <AlertDialogCancel asChild>
          <button type="button" className="govuk-button govuk-button--secondary">
            Cancel
          </button>
        </AlertDialogCancel>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
)
