'use client'

import {
  TemplateTableRow,
  templateRowKey,
} from '@/app/templates/components/template-row'
import { TemplateRowData } from '@/types/templates'

export function TemplatesList({
  templates,
  selectedIds,
  onToggle,
}: {
  templates: TemplateRowData[]
  selectedIds?: Set<string>
  onToggle?: (id: string, checked: boolean) => void
}) {
  return (
    <table className="govuk-table" aria-labelledby="templates-list-heading">
      <thead className="govuk-table__head govuk-visually-hidden">
        <tr className="govuk-table__row">
          <th scope="col" className="govuk-table__header">
            Select
          </th>
          <th scope="col" className="govuk-table__header">
            Name
          </th>
          <th scope="col" className="govuk-table__header">
            Status
          </th>
          <th scope="col" className="govuk-table__header">
            Actions
          </th>
        </tr>
      </thead>
      <tbody className="govuk-table__body">
        {templates.map((template) => (
          <TemplateTableRow
            key={templateRowKey(template)}
            template={template}
            selectedIds={selectedIds}
            onToggle={onToggle}
          />
        ))}
      </tbody>
    </table>
  )
}
