'use client'

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { TemplateData } from '@/types/templates'
import posthog from 'posthog-js'

import { useState } from 'react'

interface ExampleTemplatesDialogProps {
  onSelectTemplate: (template: TemplateData) => void
  examples: TemplateData[]
}

export function ExampleTemplatesDialog({
  onSelectTemplate,
  examples,
}: ExampleTemplatesDialogProps) {
  const [open, setOpen] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateData | null>(
    null
  )
  const handleSelectExample = (template: TemplateData) => {
    onSelectTemplate(template)
    setOpen(false)
    posthog.capture('template_example_selected', {
      example_name: template.name,
    })
  }

  const handleOpenChange = (isOpen: boolean) => {
    setOpen(isOpen)
    if (!isOpen) setSelectedTemplate(null)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild type="button">
        <button className="govuk-button govuk-button--secondary">
          Try an example
        </button>
      </DialogTrigger>
      <DialogContent wideModal>
        <div className="govuk-form-group">
          <fieldset className="govuk-fieldset">
            <legend className="govuk-fieldset__legend govuk-fieldset__legend--l">
              <DialogTitle className="govuk-fieldset__heading">
                Choose an example template
              </DialogTitle>
            </legend>
            <div
              className="govuk-radios govuk-!-margin-top-9 flex flex-wrap"
              data-module="govuk-radios"
            >
              {examples.map((template, index) => (
                <div
                  className="govuk-radios__item new-recording__radio-item md:w-1/2"
                  key={index}
                >
                  <input
                    className="govuk-radios__input"
                    id={`example-template-${index}`}
                    name="example-template"
                    type="radio"
                    value={template.name}
                    checked={selectedTemplate?.name === template.name}
                    onChange={() => setSelectedTemplate(template)}
                  />
                  <label
                    className="govuk-label govuk-radios__label"
                    htmlFor={`example-template-${index}`}
                  >
                    <div className="govuk-!-margin-bottom-2 flex items-center gap-2">
                      <h2 className="govuk-heading-s govuk-!-margin-bottom-0">
                        {template.name}
                      </h2>
                      <span className="govuk-tag govuk-tag--green">
                        {template.type === 'document' ? 'Summary' : 'Q&A'}
                      </span>
                    </div>
                    <p className="govuk-body-s">{template.description}</p>
                  </label>
                </div>
              ))}
            </div>
          </fieldset>
        </div>
        <DialogFooter>
          <div className="govuk-button-group flex justify-end">
            <button
              type="button"
              className="govuk-button govuk-button--secondary"
              onClick={() => setOpen(false)}
            >
              Close
            </button>
            <button
              type="button"
              className="govuk-button"
              disabled={!selectedTemplate}
              onClick={() =>
                selectedTemplate && handleSelectExample(selectedTemplate)
              }
            >
              Select example
            </button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
