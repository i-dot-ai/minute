'use client'

import { TranscriptionForm } from '@/components/audio/types'
import { TemplateMetadata, TemplateResponse } from '@/lib/client'
import {
  getTemplatesTemplatesGetOptions,
  getUserTemplatesUserTemplatesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { Template } from '@/types/templates'
import { useGovukModule } from '@/hooks/use-govuk-module'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { useFormContext } from 'react-hook-form'
import { cn } from '@/lib/utils'

function toFormTemplate(
  template: TemplateResponse | TemplateMetadata,
  isUserTemplate: boolean
): Template {
  if (isUserTemplate) {
    const userTemplate = template as TemplateResponse
    return {
      id: userTemplate.id,
      name: userTemplate.name,
      description: userTemplate.description,
      agenda_usage: 'not_used',
    }
  }
  const defaultTemplate = template as TemplateMetadata
  return {
    id: null,
    name: defaultTemplate.name,
    description: defaultTemplate.description,
    agenda_usage: defaultTemplate.agenda_usage,
  }
}

function getOptionValue(
  template: TemplateResponse | TemplateMetadata,
  isUserTemplate: boolean
): string {
  if (isUserTemplate) {
    return `user:${(template as TemplateResponse).id}`
  }
  return `default:${(template as TemplateMetadata).name}`
}

function resolveTemplate(
  template: Template | string,
  userTemplates: TemplateResponse[],
  defaultTemplates: TemplateMetadata[]
): Template {
  if (typeof template !== 'string') {
    return template
  }
  const userMatch = userTemplates.find((t) => t.name === template)
  if (userMatch) {
    return toFormTemplate(userMatch, true)
  }
  const defaultMatch = defaultTemplates.find((t) => t.name === template)
  if (defaultMatch) {
    return toFormTemplate(defaultMatch, false)
  }
  return {
    id: null,
    name: template,
    description: '',
    agenda_usage: 'optional',
  }
}

function getSelectedOptionValue(
  template: Template,
  userTemplates: TemplateResponse[],
  defaultTemplates: TemplateMetadata[]
): string {
  if (template.id) {
    return `user:${template.id}`
  }
  if (defaultTemplates.some((t) => t.name === template.name)) {
    return `default:${template.name}`
  }
  const userMatch = userTemplates.find((t) => t.name === template.name)
  if (userMatch) {
    return `user:${userMatch.id}`
  }
  return `default:${template.name}`
}

export const StartTranscriptionSection = ({
  fullWidth = true,
}: {
  fullWidth?: boolean
}) => {
  const form = useFormContext<TranscriptionForm>()
  const detailsRef = useRef<HTMLDetailsElement>(null)
  const selectedTemplate = form.watch('template')
  const { data: defaultTemplates = [] } = useQuery(
    getTemplatesTemplatesGetOptions()
  )
  const { data: userTemplates = [] } = useQuery(
    getUserTemplatesUserTemplatesGetOptions()
  )

  const handleTemplateChange = (optionValue: string) => {
    if (optionValue.startsWith('user:')) {
      const id = optionValue.slice('user:'.length)
      const match = userTemplates.find((t) => t.id === id)
      if (!match) return
      const formTemplate = toFormTemplate(match, true)
      form.setValue('template', formTemplate)
      if (formTemplate.agenda_usage === 'not_used') {
        form.setValue('agenda', '')
      }
      return
    }

    if (optionValue.startsWith('default:')) {
      const name = optionValue.slice('default:'.length)
      const match = defaultTemplates.find((t) => t.name === name)
      if (!match) return
      const formTemplate = toFormTemplate(match, false)
      form.setValue('template', formTemplate)
      if (formTemplate.agenda_usage === 'not_used') {
        form.setValue('agenda', '')
      }
    }
  }

  const resolvedTemplate = resolveTemplate(
    selectedTemplate,
    userTemplates,
    defaultTemplates
  )

  useEffect(() => {
    if (typeof selectedTemplate !== 'string') {
      return
    }
    const userMatch = userTemplates.find((t) => t.name === selectedTemplate)
    if (userMatch) {
      form.setValue('template', toFormTemplate(userMatch, true))
      return
    }
    const defaultMatch = defaultTemplates.find(
      (t) => t.name === selectedTemplate
    )
    if (defaultMatch) {
      form.setValue('template', toFormTemplate(defaultMatch, false))
    }
  }, [defaultTemplates, form, selectedTemplate, userTemplates])

  const selectedOptionValue = getSelectedOptionValue(
    resolvedTemplate,
    userTemplates,
    defaultTemplates
  )

  return (
    <div className="govuk-!-padding-top-6 items-start border-t border-(--govuk-border-colour)">
      <div className="govuk-form-group flex items-center gap-2">
        <label className="govuk-label" htmlFor="template">
          Summarise using:
        </label>
        <select
          className="govuk-select"
          id="template"
          value={selectedOptionValue}
          onChange={(e) => handleTemplateChange(e.target.value)}
        >
          {userTemplates.map((template) => (
            <option
              key={getOptionValue(template, true)}
              value={getOptionValue(template, true)}
            >
              {template.name}
            </option>
          ))}
          {defaultTemplates.map((template) => (
            <option
              key={getOptionValue(template, false)}
              value={getOptionValue(template, false)}
            >
              {template.name}
            </option>
          ))}
        </select>
      </div>

      {resolvedTemplate.agenda_usage != 'not_used' && (
        <div className="govuk-form-group">
          <label className="govuk-label" htmlFor="agenda">
            Agenda (
            {resolvedTemplate.agenda_usage == 'optional'
              ? 'optional'
              : 'required'}
            )
          </label>
          <textarea
            className={cn(
              'govuk-textarea',
              fullWidth ? '' : 'govuk-!-width-three-quarters'
            )}
            placeholder="Add discussion points from the meeting that should be included in the summary."
            id="agenda"
            rows={4}
            aria-describedby="agenda-hint"
            {...form.register('agenda', {
              required: resolvedTemplate.agenda_usage == 'required',
            })}
          />
        </div>
      )}
    </div>
  )
}
