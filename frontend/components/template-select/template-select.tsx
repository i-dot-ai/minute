import { useGovukModule } from '@/hooks/use-govuk-module'
import {
  getTemplatesTemplatesGetOptions,
  getUserTemplatesUserTemplatesGetOptions,
} from '@/lib/client/@tanstack/react-query.gen'
import { Template } from '@/types/templates'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { useRef } from 'react'

export const TemplateSelect = ({
  value,
  onChange,
}: {
  onChange: (template: Template) => void
  value: Template
}) => {
  return (
    <div>
      <h3 className="govuk-heading-s">Default templates</h3>
      <DefaultTemplateSelect value={value} onChange={onChange} />
      <h3 className="govuk-heading-s">Your templates</h3>
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
  const { data: templates = [], isLoading } = useQuery(
    getTemplatesTemplatesGetOptions()
  )
  const radiosRef = useRef<HTMLDivElement>(null)
  const canInitRadios = !isLoading && templates.length > 0

  useGovukModule(radiosRef, 'Radios', canInitRadios)

  if (isLoading) {
    return <p className="govuk-body">Loading templates...</p>
  }

  return (
    <div
      ref={radiosRef}
      className="govuk-radios upload-radio__flex-container"
      data-module="govuk-radios"
    >
      {templates.map((template) => {
        const radioId = `DEFAULT::${template.name}`
        const checked = value.id === null && value.name === template.name

        return (
          <div key={radioId} className="govuk-radios__item upload-radio__item">
            <input
              className="govuk-radios__input"
              id={radioId}
              name="template"
              type="radio"
              checked={checked}
              value={radioId}
              onChange={() => {
                const selectedTemplate = templates.find(
                  (t) => `DEFAULT::${t.name}` === radioId
                )

                if (selectedTemplate) {
                  onChange({
                    id: null,
                    name: selectedTemplate.name,
                    agenda_usage: selectedTemplate.agenda_usage,
                  })
                }
              }}
            />
            <label
              className="govuk-label govuk-radios__label"
              htmlFor={radioId}
            >
              <p className="govuk-body govuk-!-margin-bottom-1 govuk-!-font-weight-bold">
                {template.name}
              </p>
              <p className="govuk-body-s">{template.description}</p>
            </label>
          </div>
        )
      })}
    </div>
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
  const customRadiosRef = useRef<HTMLDivElement>(null)
  const canInitRadios = !isLoading && templates.length > 0

  useGovukModule(customRadiosRef, 'Radios', canInitRadios)

  if (isLoading) {
    return <p className="govuk-body">Loading templates...</p>
  }

  if (!templates.length) {
    return (
      <p className="govuk-body">
        You haven&apos;t made any templates yet. Go to the{' '}
        <Link href="/templates/new" className="govuk-link">
          templates page
        </Link>{' '}
        to create and edit your templates.
      </p>
    )
  }

  return (
    <div
      ref={customRadiosRef}
      className="govuk-radios upload-radio__flex-container"
      data-module="govuk-radios"
    >
      {templates.map((template) => {
        const checked = value.id === template.id

        return (
          <div key={template.id} className="govuk-radios__item upload-radio__item">
            <input
              className="govuk-radios__input"
              id={template.id!}
              name="template"
              type="radio"
              checked={checked}
              value={template.id!}
              onChange={() => {
                const selectedTemplate = templates.find(
                  (t) => t.id === template.id
                )

                if (selectedTemplate) {
                  onChange({
                    id: selectedTemplate.id!,
                    name: selectedTemplate.name,
                    agenda_usage: 'not_used',
                  })
                }
              }}
            />
            <label
              className="govuk-label govuk-radios__label"
              htmlFor={template.id!}
            >
              <p className="govuk-body govuk-!-margin-bottom-1 govuk-!-font-weight-bold">
                {template.name}
              </p>
              <p className="govuk-body-s">{template.description}</p>
            </label>
          </div>
        )
      })}
    </div>
  )
}
