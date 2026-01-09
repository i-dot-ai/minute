import { TemplateRadioGroup } from '@/components/template-select/template-radio-group'
import {
  getTemplatesTemplatesGetOptions,
  getUserTemplatesUserTemplatesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { Template } from '@/types/templates'
import { useQuery } from '@tanstack/react-query'
import { FileText } from 'lucide-react'

export const TemplateSelect = ({
  value,
  onChange,
}: {
  onChange: (template: Template) => void
  value: Template
}) => {
  return (
    <div>
      <DefaultTemplateSelect value={value} onChange={onChange} />
      <h4 className="font-bold">Your templates</h4>
      <UserTemplateSelect value={value} onChange={onChange} />
    </div>
  )
}

export const DefaultTemplateSelect = ({
  onChange,
  value,
}: {
  onChange: (template: Template) => void
  value: Template
}) => {
  const { data: templates = [], isLoading: isLoadingTemplates } = useQuery(
    getTemplatesTemplatesGetOptions()
  )
  return (
    <TemplateRadioGroup
      templates={templates.map((t) => ({
        id: `DEFAULT::${t.name}`, // Prefix to stop name clashes between default and user templates
        name: t.name,
        description: t.description,
      }))}
      onChange={(id) => {
        const selectedTemplate = templates.find(
          (t) => `DEFAULT::${t.name}` === id
        )
        if (selectedTemplate) {
          onChange({
            id: null,
            name: selectedTemplate.name,
            agenda_usage: selectedTemplate.agenda_usage,
          })
        }
      }}
      value={`DEFAULT::${value.name}`}
      isLoading={isLoadingTemplates}
    />
  )
}
export const UserTemplateSelect = ({
  onChange,
  value,
}: {
  onChange: (template: Template) => void
  value: Template
}) => {
  const { data: templates = [], isLoading } = useQuery(
    getUserTemplatesUserTemplatesGetOptions()
  )
  if (!isLoading && !templates.length) {
    return (
      <p className="text-muted-foreground mb-4 flex items-center gap-1 text-sm">
        You haven&apos;t made any templates yet. Click the
        <FileText className="inline" size="1rem" /> button above to create and
        edit your templates.
      </p>
    )
  }
  return (
    <TemplateRadioGroup
      templates={templates.map((t) => ({
        id: t.id!,
        name: t.name,
        description: t.description || '',
      }))}
      onChange={(id) => {
        const selectedTemplate = templates.find((t) => t.id === id)
        if (selectedTemplate) {
          onChange({
            id: selectedTemplate.id!,
            name: selectedTemplate.name,
            agenda_usage: 'not_used',
          })
        }
      }}
      value={value.id!}
      isLoading={isLoading}
    />
  )
}
