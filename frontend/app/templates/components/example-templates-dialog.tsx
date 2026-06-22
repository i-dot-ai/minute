'use client'

import {
  Dialog,
  DialogContent,
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
  const handleSelectExample = (template: TemplateData) => {
    onSelectTemplate(template)
    setOpen(false)
    posthog.capture('template_example_selected', {
      example_name: template.name,
    })
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild type="button">
        <button className="govuk-button govuk-button--secondary">
          Try an example
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle className="govuk-heading-l">
          Choose an example template
        </DialogTitle>
        <ul className="govuk-list">
          {examples.map((template, index) => (
            <li
              key={index}
              className="homepage__list-item govuk-!-padding-top-3 flex items-center justify-between"
            >
              <div>
                <button
                  onClick={() => handleSelectExample(template)}
                  className="govuk-link"
                >
                  <h2 className="govuk-heading-m govuk-!-margin-bottom-1">
                    {template.name}
                  </h2>
                </button>
                <p className="govuk-body">{template.description}</p>
              </div>
            </li>
          ))}
        </ul>
        <div className="govuk-button-group">
          <button
            type="button"
            className="govuk-button govuk-button--secondary"
            onClick={() => setOpen(false)}
          >
            Close
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
